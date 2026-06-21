"""Part 3 - break reach apart by type of pay (the two-part / hurdle design).

Data-review finding: the six leaf buckets are badly zero-inflated (option_grants
positive in only ~18% of firm-years), so a naive log is impossible. We split the
signal:

  * extensive margin - a 0/1 "does the firm use bucket b" (coverage).
  * intensive margin - the same median regression as Parts 1-2, fit ONLY on rows
    where the bucket is positive, giving a clean reach^(b).

Divergence D = Var_b( log reach^(b) ) is taken over the buckets actually present
for a firm-year, requiring >= DIVERGENCE_MIN_BUCKETS present.

Two granularities: a well-populated 3-bucket headline (Fixed / STI / LTI) and the
6 leaf buckets as detail. An asinh full-panel variant is provided for robustness.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from . import config as cfg


def _leaf_real_col(leaf: str) -> str:
    """Map a plan bucket name to its board real-euro column."""
    if leaf == "other_annual_comp":
        return "other_annual_bt_real"
    return f"{leaf}_bt_real"


def _base_frame(firm_year: pd.DataFrame) -> pd.DataFrame:
    """Firm-years with valid RHS (same sample as Part 1)."""
    df = firm_year.rename(columns={"OPRE": "opre", "ROA": "roa", "GEAR": "gear"})
    df = df.dropna(subset=["opre", "roa", "gear"])
    df = df[df["opre"] > 0].copy()
    df["lopre"] = np.log(df["opre"])
    df["year"] = df["year"].astype(int)
    return df


def bucket_values(firm_year: pd.DataFrame, scheme: str = "3") -> pd.DataFrame:
    """Long table: one row per (isin, year, bucket) with the bucket's real value.

    scheme="3" -> Fixed/STI/LTI ; scheme="6" -> the six leaf buckets.
    """
    base = _base_frame(firm_year)
    keep = ["isin", "year", "opre", "roa", "gear", "lopre"]

    if scheme == "6":
        spec = {b: [b] for b in cfg.BUCKETS_6}
    elif scheme == "3":
        spec = cfg.BUCKETS_3
    else:
        raise ValueError("scheme must be '3' or '6'")

    out = []
    for bucket, leaves in spec.items():
        cols = [_leaf_real_col(l) for l in leaves]
        val = base[cols].sum(axis=1, min_count=1)
        part = base[keep].copy()
        part["bucket"] = bucket
        part["value"] = val.values
        out.append(part)
    return pd.concat(out, ignore_index=True)


def fit_bucket_reach(firm_year: pd.DataFrame, scheme: str = "3",
                     q: float = 0.5) -> dict:
    """Intensive-margin reach per bucket + extensive-margin coverage."""
    long = bucket_values(firm_year, scheme=scheme)
    rows, betas, coverage = [], {}, {}

    for bucket, g in long.groupby("bucket"):
        n_all = len(g)
        used = g["value"] > 0
        coverage[bucket] = {"n": n_all, "n_used": int(used.sum()),
                            "share_used": float(used.mean())}
        gp = g[used].copy()
        gp["lval"] = np.log(gp["value"])
        m = smf.quantreg("lval ~ lopre + roa + gear + C(year)", gp).fit(q=q)
        beta_b = float(m.params["lopre"])
        betas[bucket] = beta_b
        gp["eps_b"] = gp["lval"] - m.fittedvalues
        gp["reach_b"] = np.exp(gp["eps_b"] / beta_b)     # size-equivalent (per-form beta)
        gp["premium_b"] = np.exp(gp["eps_b"])            # % above/below the form's norm
        rows.append(gp[["isin", "year", "bucket", "value", "reach_b", "premium_b"]])

    reach_long = pd.concat(rows, ignore_index=True)
    return {"reach_long": reach_long, "betas": betas, "coverage": coverage,
            "scheme": scheme}


def divergence(reach_long: pd.DataFrame,
               min_buckets: int = cfg.DIVERGENCE_MIN_BUCKETS) -> pd.DataFrame:
    """The plan's spread measure D_it = Var_b( log reach^(b) ), kept for
    faithfulness but WINSORIZED (log reach clipped to +/-log(20)) so that a single
    near-zero or runaway bucket cannot dominate. NOTE: variance is symmetric, so
    it also fires on firms that simply pay ~nothing in a bucket - use
    `hidden_stretch` for the direction-aware (overpayment) signal."""
    df = reach_long.copy()
    lo, hi = np.log(0.05), np.log(20.0)
    df["log_reach"] = np.log(df["reach_b"]).clip(lo, hi)
    g = df.groupby(["isin", "year"])["log_reach"]
    out = g.agg(n_buckets="count", divergence="var").reset_index()
    out = out[out["n_buckets"] >= min_buckets].copy()
    return out.sort_values("divergence", ascending=False).reset_index(drop=True)


def hidden_stretch(reach_long: pd.DataFrame, total_reach: pd.DataFrame | None = None,
                   min_buckets: int = cfg.DIVERGENCE_MIN_BUCKETS) -> pd.DataFrame:
    """Direction-aware 'hidden stretch' - the Part-3 deliverable, made internally
    consistent (the headline IS the sum of the parts).

    For each firm-year we compare each pay form to *its own* size benchmark
    (premium^(b) = exp(eps_b)). The headline is then the pay-weighted overall
    premium implied by the parts:

        headline = sum_b(form value)  /  sum_b(form benchmark),   benchmark_b = value_b / premium_b

    i.e. exactly "what the parts add up to vs what they should". Because the
    headline is a weighted average of the form premiums, the most-stretched form is
    always >= the headline, so:

        hidden_stretch = log( max_b premium^(b) )  -  log( headline )   >= 0

    It is a pure CONCENTRATION measure: 0 = pay sits evenly across forms; large =
    excess piled into ONE form (named in `worst_bucket`) far above the firm's own
    average. (`total_reach` is accepted for backward-compatibility but no longer
    used - the headline now comes from the parts, not a separate total regression.)
    """
    val = reach_long.pivot_table(index=["isin", "year"], columns="bucket", values="value")
    prem = reach_long.pivot_table(index=["isin", "year"], columns="bucket", values="premium_b")
    bench = val / prem                                   # implied benchmark euros per form
    out = pd.DataFrame({
        "n_buckets": prem.notna().sum(axis=1),
        "worst_bucket": prem.idxmax(axis=1),
        "worst_form_premium": prem.max(axis=1),
        "total_premium": val.sum(axis=1, min_count=1) / bench.sum(axis=1, min_count=1),
    }).reset_index()
    out = out[(out["n_buckets"] >= min_buckets) &
              (out["worst_form_premium"] > 0) & (out["total_premium"] > 0)].copy()
    out["hidden_stretch"] = (np.log(out["worst_form_premium"])
                             - np.log(out["total_premium"]))
    return out.sort_values("hidden_stretch", ascending=False).reset_index(drop=True)


def asinh_bucket_reach(firm_year: pd.DataFrame, scheme: str = "3",
                       q: float = 0.5) -> dict:
    """Robustness variant: asinh on the FULL panel (zeros included) instead of
    log on the positive subsample. Not the headline - just a stability check."""
    long = bucket_values(firm_year, scheme=scheme)
    rows, betas = [], {}
    for bucket, g in long.groupby("bucket"):
        gp = g.copy()
        gp["av"] = np.arcsinh(gp["value"].fillna(0.0))
        m = smf.quantreg("av ~ lopre + roa + gear + C(year)", gp).fit(q=q)
        beta_b = float(m.params["lopre"])
        betas[bucket] = beta_b
        gp["eps_b"] = gp["av"] - m.fittedvalues
        gp["reach_b"] = np.exp(gp["eps_b"] / beta_b)
        rows.append(gp[["isin", "year", "bucket", "value", "reach_b"]])
    return {"reach_long": pd.concat(rows, ignore_index=True), "betas": betas,
            "scheme": scheme}


if __name__ == "__main__":
    # SEE where Fixed/STI/LTI come from:  python -m src.part3_buckets
    from . import part0_clean
    cfg.enable_utf8_stdout()

    print("=" * 72)
    print("Fixed / STI / LTI are NOT columns in the dataset.")
    print("They are GROUPINGS of the raw board (_bt) columns, defined in")
    print("config.BUCKETS_3 and built by bucket_values() below:")
    print("=" * 72)
    for hb, leaves in cfg.BUCKETS_3.items():
        cols = [_leaf_real_col(l) for l in leaves]
        print(f"   {hb:6s} = {' + '.join(cols)}")

    fy = part0_clean.build_firm_year()

    # concrete example: a firm-year IN the regression sample using all components
    base = _base_frame(fy)
    m = (base["salary_bt_real"] > 0) & (base["one_year_bonus_bt_real"] > 0) & \
        (base["total_equity_grants_bt_real"] > 0)
    ex = base[m].sort_values("total_comp_bt_real", ascending=False).iloc[0]
    print(f"\nExample (in-sample): {ex['company_shortname']} {int(ex['year'])} "
          f"(real EUR thousands)")
    fixed = ex["salary_bt_real"] + ex["other_annual_bt_real"]
    sti = ex["one_year_bonus_bt_real"]
    lti = ex["total_equity_grants_bt_real"] + ex["multi_year_bonus_grants_bt_real"]
    print(f"   salary {ex['salary_bt_real']:.0f} + other_annual {ex['other_annual_bt_real']:.0f}"
          f"  -> Fixed = {fixed:.0f}")
    print(f"   one_year_bonus                       -> STI   = {sti:.0f}")
    print(f"   equity {ex['total_equity_grants_bt_real']:.0f} + MYB_grants "
          f"{ex['multi_year_bonus_grants_bt_real']:.0f} -> LTI   = {lti:.0f}")

    print("\nCoverage (extensive margin) and reach slope beta_b per bucket:")
    res = fit_bucket_reach(fy, scheme="3")
    for b, cov in res["coverage"].items():
        print(f"   {b:6s}: used in {cov['share_used']*100:5.1f}% of firm-years "
              f"(n_used={cov['n_used']:4d})   beta_b={res['betas'][b]:+.3f}")
