"""Part 6 - assemble the governance red flags (the deliverable).

Three flags are defined here (the others reuse earlier parts: high reach = Part 2,
high divergence = Part 3):

  * Asymmetric ratchet  - pay rises on good results but is sticky on bad
        d log pay = a + b_up * d roa * 1[d roa>0] + b_dn * d roa * 1[d roa<0]
        flag if b_up >> b_dn ~ 0.
  * Secrecy premium      - firms that opted out of individual disclosure
        log reach = a + rho * opting_out + g1 roa + g2 gear + delta_t
        flag if rho > 0.  (log reach used instead of level reach for robustness
        to the fat right tail; sign of rho is unchanged.)
  * Internal concentration - CEO pay vs the median other executive, over time
        C = total_comp(CEO) / median(total_comp of non-CEO execs)
        flag if C rises over t.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf


def asymmetric_ratchet(firm_year: pd.DataFrame,
                       pay_col: str = "total_comp_bt_real") -> dict:
    df = firm_year.rename(columns={"ROA": "roa"})[["isin", "year", "roa"]].copy()
    df["pay"] = firm_year[pay_col]
    df = df.dropna(subset=["roa", "pay"])
    df = df[df["pay"] > 0].sort_values(["isin", "year"])
    df["lpay"] = np.log(df["pay"])
    g = df.groupby("isin")
    df["d_lpay"] = g["lpay"].diff()
    df["d_roa"] = g["roa"].diff()
    df["yr_step"] = g["year"].diff()
    d = df[(df["yr_step"] == 1)].dropna(subset=["d_lpay", "d_roa"]).copy()
    d["droa_up"] = d["d_roa"].clip(lower=0)
    d["droa_dn"] = d["d_roa"].clip(upper=0)
    m = smf.ols("d_lpay ~ droa_up + droa_dn", d).fit()
    return {"n": int(len(d)),
            "beta_up": float(m.params["droa_up"]),
            "beta_dn": float(m.params["droa_dn"]),
            "p_up": float(m.pvalues["droa_up"]),
            "p_dn": float(m.pvalues["droa_dn"]),
            "flag": bool(m.params["droa_up"] > m.params["droa_dn"]
                         and m.pvalues["droa_up"] < 0.1)}


def secrecy_premium(reach_frame: pd.DataFrame, firm_year: pd.DataFrame) -> dict:
    """reach_frame: Part-2 output with isin, year, reach, roa, gear."""
    opt = firm_year[["isin", "year", "opting_out"]].copy()
    df = reach_frame.merge(opt, on=["isin", "year"], how="left")
    df = df.dropna(subset=["reach", "opting_out", "roa", "gear"])
    df = df[df["reach"] > 0].copy()
    df["log_reach"] = np.log(df["reach"])
    df["year"] = df["year"].astype(int)
    m = smf.ols("log_reach ~ opting_out + roa + gear + C(year)", df).fit()
    return {"n": int(len(df)), "rho": float(m.params["opting_out"]),
            "p": float(m.pvalues["opting_out"]),
            "flag": bool(m.params["opting_out"] > 0 and m.pvalues["opting_out"] < 0.1)}


def redflag_ranking(firm_year: pd.DataFrame, reach_frame: pd.DataFrame,
                    hidden_tbl: pd.DataFrame,
                    concentration_byyear: pd.DataFrame) -> pd.DataFrame:
    """Rank firms by a composite red-flag score across the per-firm flags:

        excessive pay   = median reach            (Part 2)
        hidden stretch  = median hidden_stretch   (Part 3, direction-aware)
        secrecy         = share of years opted out (Part 6)
        concentration   = median CEO/other ratio  (Part 6)

    Each metric is turned into a cross-firm percentile (higher = worse) so the
    fat-tailed reach does not dominate; the composite is the mean of available
    percentiles. (Asymmetric ratchet is a market-level regression, and portable
    rent is Part 5/deferred, so neither enters the per-firm table.)
    """
    name = (firm_year.dropna(subset=["isin"])
            .drop_duplicates("isin").set_index("isin")["company_shortname"])

    reach_f = reach_frame.groupby("isin")["reach"].median().rename("median_reach")
    n_years = reach_frame.groupby("isin")["reach"].size().rename("n_years")
    hidden_f = hidden_tbl.groupby("isin")["hidden_stretch"].median().rename("median_hidden")
    secrecy_f = firm_year.groupby("isin")["opting_out"].mean().rename("secrecy_share")
    conc_f = concentration_byyear.groupby("isin")["C"].median().rename("median_C")

    df = pd.concat([name.rename("company"), n_years, reach_f, hidden_f,
                    secrecy_f, conc_f], axis=1)
    df = df[df["median_reach"].notna()].copy()

    metrics = ["median_reach", "median_hidden", "secrecy_share", "median_C"]
    ranks = []
    for m in metrics:
        pr = df[m].rank(pct=True)          # 0..1, higher value -> higher pct
        df[m + "_pct"] = pr
        ranks.append(pr)
    df["score"] = pd.concat(ranks, axis=1).mean(axis=1, skipna=True)
    df = df.sort_values("score", ascending=False)
    df.insert(0, "rank", range(1, len(df) + 1))
    return df.reset_index()


def redflag_to_latex(ranking: pd.DataFrame, path, top: int = 15) -> None:
    """Write a booktabs tabular of the top-`top` firms for \\input into the report."""
    cols = [("rank", "Rank", "{:d}"), ("company", "Company", "{:s}"),
            ("median_reach", "Reach", "{:.1f}"),
            ("median_hidden", "Hidden", "{:.2f}"),
            ("secrecy_share", "Secrecy", "{:.0%}"),
            ("median_C", "CEO ratio", "{:.2f}"),
            ("score", "Score", "{:.2f}")]
    sub = ranking.head(top)
    lines = [r"\begin{tabular}{rlrrrrr}", r"\toprule",
             " & ".join(h for _, h, _ in cols) + r" \\", r"\midrule"]
    for _, row in sub.iterrows():
        cells = []
        for key, _, fmt in cols:
            v = row[key]
            if pd.isna(v):
                cells.append("--")
            elif key == "company":
                cells.append(str(v).replace("&", r"\&"))
            elif key == "secrecy_share":
                cells.append(fmt.format(v).replace("%", r"\%"))
            else:
                cells.append(fmt.format(v))
        lines.append(" & ".join(cells) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}"]
    Path(path).write_text("\n".join(lines), encoding="utf-8")


def internal_concentration(person_year: pd.DataFrame) -> dict:
    """C_jt = CEO pay / median non-CEO pay, and whether it trends up over time.

    Uses raw reported total_comp (the ratio cancels deflation)."""
    p = person_year[["isin", "year", "ceo_flag_eoy", "total_comp"]].copy()
    p = p.dropna(subset=["total_comp"])
    p["is_ceo"] = (p["ceo_flag_eoy"] == 1)

    recs = []
    for (isin, year), g in p.groupby(["isin", "year"]):
        ceo = g[g["is_ceo"]]["total_comp"]
        others = g[~g["is_ceo"]]["total_comp"]
        if len(ceo) == 0 or len(others) == 0:
            continue
        med = others.median()
        if med <= 0:
            continue
        recs.append({"isin": isin, "year": int(year),
                     "C": float(ceo.max() / med)})
    cdf = pd.DataFrame(recs)
    # trend of C over time (pooled OLS); flag if slope > 0
    m = smf.ols("C ~ year", cdf).fit()
    by_year = cdf.groupby("year")["C"].median()
    return {"n": int(len(cdf)), "median_C": float(cdf["C"].median()),
            "slope_per_year": float(m.params["year"]),
            "p": float(m.pvalues["year"]),
            "C_first_year": float(by_year.iloc[0]),
            "C_last_year": float(by_year.iloc[-1]),
            "flag": bool(m.params["year"] > 0 and m.pvalues["year"] < 0.1),
            "by_year": cdf}


if __name__ == "__main__":
    # Inspect the red flags:  python -m src.part6_redflags
    from . import config as cfg, part0_clean, part1_benchmark, part2_reach, part3_buckets
    cfg.enable_utf8_stdout()
    fy = part0_clean.build_firm_year()
    py = part0_clean.build_person_year()
    fit = part1_benchmark.fit_benchmark(fy)
    reach = part2_reach.reach_from_benchmark(fit)
    reach_long = part3_buckets.fit_bucket_reach(fy, "3")["reach_long"]
    hs3 = part3_buckets.hidden_stretch(reach_long, reach)

    rt = asymmetric_ratchet(fy)
    print(f"Asymmetric ratchet : beta_up={rt['beta_up']:+.3f} beta_dn={rt['beta_dn']:+.3f}"
          f"  flag={rt['flag']}  (no asymmetry -> no ratchet)")
    sc = secrecy_premium(reach, fy)
    print(f"Secrecy premium    : rho={sc['rho']:+.3f} (p={sc['p']:.3f})  flag={sc['flag']}"
          f"  (opting-out firms carry higher reach)")
    cc = internal_concentration(py)
    print(f"CEO concentration  : median C={cc['median_C']:.2f}, "
          f"{cc['C_first_year']:.2f} -> {cc['C_last_year']:.2f} "
          f"(p={cc['p']:.3f})  flag={cc['flag']}")

    rk = redflag_ranking(fy, reach, hs3, cc["by_year"])
    print("\nCross-flag ranking - top 10 firms:")
    print(rk.head(10)[["rank", "company", "median_reach", "median_hidden",
                       "secrecy_share", "median_C", "score"]].to_string(index=False))
