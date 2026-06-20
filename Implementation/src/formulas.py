"""
Formula implementations from exec_pay_full_guide.pdf.

Part 0: (1) annualize, (2) deflate
Part 1: (3) median benchmark, (4) residual epsilon
Part 2: (5)-(6) phantom size and reach
Part 3: (8) bucket reach and divergence
Part 4: (9) treadmill decomposition
Part 5: (10)-(11) movers and event-study tau_k
Part 6: (13)-(15) ratchet, secrecy, CEO concentration
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm
from statsmodels.regression.quantile_regression import QuantReg


# ---------------------------------------------------------------------------
# Part 0 — Formulas (1) and (2)
# ---------------------------------------------------------------------------

def annualize_pay(pay_raw: pd.Series, fy_days: pd.Series, days_in_post: pd.Series) -> pd.Series:
    """Formula (1): pay_ann = pay_raw × L_it / d_it."""
    return pay_raw * (fy_days / days_in_post.clip(lower=1))


def deflate_pay(pay_ann: pd.Series, cpi: pd.Series, cpi_base: float) -> pd.Series:
    """Formula (2): pay_real = pay_ann / (CPI_t / CPI_t*)."""
    return pay_ann / (cpi / cpi_base)


# ---------------------------------------------------------------------------
# Part 1 — Formulas (3) and (4)
# ---------------------------------------------------------------------------

def fit_median_benchmark(
    df: pd.DataFrame,
    y_col: str = "pay_real",
    peer_label: str | None = None,
) -> tuple[pd.DataFrame, dict]:
    """
    Formula (3): Q_0.5(log pay) = α + β·log(OPRE) + γ1·ROA + γ2·GEAR + δ_t
    Formula (4): ε = log pay − fitted
    """
    sub = df.copy()
    sub["log_pay"] = np.log(sub[y_col].clip(lower=1e-6))
    sub["log_opre"] = np.log(sub["OPRE"].clip(lower=1e-6))

    year_dum = pd.get_dummies(sub["year"].astype(int), prefix="yr", drop_first=True)
    x_cols = pd.concat([sub[["log_opre", "ROA", "GEAR"]], year_dum], axis=1).astype(float)
    X = sm.add_constant(x_cols, has_constant="add").astype(float)
    y = sub["log_pay"].astype(float)

    model = QuantReg(y, X).fit(q=0.5)
    fitted = model.predict(X)
    sub["residual"] = sub["log_pay"] - fitted
    sub["fitted_log_pay"] = fitted

    beta = float(model.params["log_opre"])
    params = {
        "peer_label": peer_label or "ALL",
        "alpha": float(model.params["const"]),
        "beta": beta,
        "gamma_roa": float(model.params["ROA"]),
        "gamma_gear": float(model.params["GEAR"]),
        "n": len(sub),
    }

    for col in model.params.index:
        if col.startswith("yr_"):
            params[col] = float(model.params[col])

    # Attach year effect δ_t per row (reference year = 0)
    sub["delta_t"] = 0.0
    for col in model.params.index:
        if col.startswith("yr_"):
            yr = int(col.replace("yr_", ""))
            sub.loc[sub["year"] == yr, "delta_t"] = float(model.params[col])

    sub["alpha"] = params["alpha"]
    sub["beta"] = beta
    sub["gamma_roa"] = params["gamma_roa"]
    sub["gamma_gear"] = params["gamma_gear"]

    return sub, params


# ---------------------------------------------------------------------------
# Part 2 — Formulas (5) and (6)
# ---------------------------------------------------------------------------

def compute_reach(df: pd.DataFrame) -> pd.DataFrame:
    """
    Formula (5): log S_phantom = (log pay − α − γ1·ROA − γ2·GEAR − δ_t) / β
                  reach = S_phantom / OPRE
    Formula (6): reach = exp(ε / β)   [algebraically equivalent]
    """
    out = df.copy()
    beta = out["beta"].replace(0, np.nan).fillna(0.3)

    # Formula (6) — clip extreme values for numerical stability
    out["reach"] = np.exp(out["residual"] / beta).clip(lower=0.01, upper=500)

    # Formula (5) — phantom size (validation column)
    log_s_phantom = (
        out["log_pay"] - out["alpha"] - out["gamma_roa"] * out["ROA"]
        - out["gamma_gear"] * out["GEAR"] - out["delta_t"]
    ) / beta
    out["s_phantom"] = np.exp(log_s_phantom).clip(lower=0, upper=1e15)
    out["reach_phantom"] = (out["s_phantom"] / out["OPRE"].clip(lower=1e-6)).clip(lower=0.01, upper=500)

    return out


# ---------------------------------------------------------------------------
# Part 3 — Formula (8)
# ---------------------------------------------------------------------------

def compute_divergence(df: pd.DataFrame, reach_bucket_cols: list[str]) -> pd.Series:
    """Formula (8): D_it = Var_b(log reach^(b)_it)."""
    log_reach = df[reach_bucket_cols].apply(lambda c: np.log(c.clip(lower=0.01)))
    return log_reach.var(axis=1)


# ---------------------------------------------------------------------------
# Part 4 — Formula (9) treadmill decomposition
# ---------------------------------------------------------------------------

def treadmill_decomposition(xf: pd.DataFrame, year_first: int, year_last: int) -> dict:
    """
    Formula (9):
      Δlog pay = b'_0·(Z̄_T − Z̄_0) + Z̄'_T·(b_T − b_0)
      Z_it = (log OPRE, ROA, GEAR)
    """
    xf = xf.copy()
    xf["log_pay"] = np.log(xf["pay_real"].clip(lower=1e-6))
    xf["log_opre"] = np.log(xf["OPRE"].clip(lower=1e-6))

    sub0 = xf[xf["year"] == year_first]
    subT = xf[xf["year"] == year_last]
    if len(sub0) < 5 or len(subT) < 5:
        return {}

    z_cols = ["log_opre", "ROA", "GEAR"]
    z_bar_0 = sub0[z_cols].mean()
    z_bar_T = subT[z_cols].mean()

    _, p0 = fit_median_benchmark(sub0, peer_label=f"year_{year_first}")
    _, pT = fit_median_benchmark(subT, peer_label=f"year_{year_last}")

    b0 = np.array([p0["beta"], p0["gamma_roa"], p0["gamma_gear"]])
    bT = np.array([pT["beta"], pT["gamma_roa"], pT["gamma_gear"]])

    delta_log_pay = subT["log_pay"].mean() - sub0["log_pay"].mean()
    fundamentals = float(np.dot(b0, (z_bar_T - z_bar_0).values))
    drift = float(np.dot(z_bar_T.values, (bT - b0)))
    treadmill_share = drift / delta_log_pay if abs(delta_log_pay) > 1e-9 else np.nan

    return {
        "year_first": year_first,
        "year_last": year_last,
        "delta_log_pay": delta_log_pay,
        "fundamentals_component": fundamentals,
        "treadmill_component": drift,
        "treadmill_share": treadmill_share,
        "b0_beta": p0["beta"],
        "bT_beta": pT["beta"],
    }


def extract_year_effects(models: pd.DataFrame) -> pd.DataFrame:
    """Part 4 Route A: plot δ_t from Part 1 models."""
    rows = []
    for _, m in models.iterrows():
        peer = m["peer_label"]
        for col in m.index:
            if str(col).startswith("yr_"):
                year = int(str(col).replace("yr_", ""))
                rows.append({"peer_label": peer, "year": year, "delta_t": m[col]})
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Part 5 — Formulas (10) and (11)
# ---------------------------------------------------------------------------

def count_movers(links: pd.DataFrame) -> pd.DataFrame:
    """Formula (10): M_i = #{ISIN : exec_id = i}; movers if M_i > 1."""
    counts = links.groupby("exec_id")["isin"].nunique().reset_index(name="M_i")
    counts["is_mover"] = counts["M_i"] > 1
    return counts


def mobility_event_study(
    xp: pd.DataFrame,
    xf_reach: pd.DataFrame,
    mover_ids: pd.Index,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Formula (11): τ_k = average reach at event time k relative to job change.
    Event study estimates τ_k by mean reach at t − move_i = k.
    """
    xp_m = xp[xp["exec_id"].isin(mover_ids)].merge(
        xf_reach[["isin", "year", "reach", "peer_label"]],
        on=["isin", "year"],
        how="left",
    )

    events = []
    for eid, grp in xp_m.sort_values(["exec_id", "year"]).groupby("exec_id"):
        grp = grp.sort_values("year")
        isins = grp["isin"].tolist()
        for i in range(1, len(grp)):
            if isins[i] != isins[i - 1]:
                move_year = int(grp.iloc[i]["year"])
                window = xp_m[
                    (xp_m["exec_id"] == eid) & (xp_m["year"].between(move_year - 2, move_year + 2))
                ]
                for _, row in window.iterrows():
                    events.append(
                        {
                            "exec_id": eid,
                            "move_year": move_year,
                            "event_t": int(row["year"] - move_year),
                            "reach": row["reach"],
                            "tau_k": row["reach"],  # τ_k estimate = mean at k
                        }
                    )

    events_df = pd.DataFrame(events)
    if len(events_df) == 0:
        return events_df, pd.DataFrame(columns=["event_t", "tau_k", "n"])

    tau = (
        events_df.groupby("event_t")
        .agg(tau_k=("reach", "mean"), n=("exec_id", "count"))
        .reset_index()
    )
    return events_df, tau


# ---------------------------------------------------------------------------
# Part 6 — Formulas (13), (14), (15)
# ---------------------------------------------------------------------------

def fit_asymmetric_ratchet(xf: pd.DataFrame) -> dict:
    """
    Formula (13): Δlog pay = a + β↑·ΔROA·1[ΔROA>0] + β↓·ΔROA·1[ΔROA<0] + e
    Flag when β↑ >> β↓ ≈ 0.
    """
    df = xf.sort_values(["isin", "year"]).copy()
    df["dlog_pay"] = df.groupby("isin")["pay_real"].transform(lambda s: np.log(s.clip(lower=1)).diff())
    df["droa"] = df.groupby("isin")["ROA"].diff()
    df = df.dropna(subset=["dlog_pay", "droa"])

    df["droa_pos"] = df["droa"].clip(lower=0)
    df["droa_neg"] = df["droa"].clip(upper=0)

    X = sm.add_constant(df[["droa_pos", "droa_neg"]]).astype(float)
    y = df["dlog_pay"].astype(float)
    model = sm.OLS(y, X).fit()

    beta_up = float(model.params["droa_pos"])
    beta_down = float(model.params["droa_neg"])
    return {
        "alpha": float(model.params["const"]),
        "beta_up": beta_up,
        "beta_down": beta_down,
        "flag_ratchet": beta_up > 0 and abs(beta_down) < 0.05 * max(abs(beta_up), 1e-6),
        "n": int(model.nobs),
    }


def fit_secrecy_premium(xf: pd.DataFrame) -> dict:
    """
    Formula (14): reach = a + ρ·opting_out + γ1·ROA + γ2·GEAR + δ_t + u
    Flag when ρ > 0.
    """
    df = xf.dropna(subset=["reach", "ROA", "GEAR", "opting_out"]).copy()
    df = df[np.isfinite(df["reach"])]
    year_dum = pd.get_dummies(df["year"].astype(int), prefix="yr", drop_first=True)
    X = sm.add_constant(pd.concat([df[["opting_out", "ROA", "GEAR"]], year_dum], axis=1)).astype(float)
    y = df["reach"].astype(float)
    model = sm.OLS(y, X).fit()

    rho = float(model.params["opting_out"])
    return {
        "rho": rho,
        "rho_pvalue": float(model.pvalues["opting_out"]),
        "flag_secrecy_premium": rho > 0 and model.pvalues["opting_out"] < 0.10,
        "n": int(model.nobs),
    }


def compute_ceo_concentration(xp: pd.DataFrame) -> pd.DataFrame:
    """
    Formula (15): C_jt = CEO pay / median(other exec pay) at firm j, year t.
    """
    ceo = xp[xp["ceo_flag_eoy"] == 1][["isin", "year", "pay_real"]].rename(columns={"pay_real": "ceo_pay"})
    others = (
        xp[xp["ceo_flag_eoy"] != 1]
        .groupby(["isin", "year"])["pay_real"]
        .median()
        .reset_index(name="median_other_pay")
    )
    conc = ceo.merge(others, on=["isin", "year"], how="inner")
    conc["C_jt"] = conc["ceo_pay"] / conc["median_other_pay"].clip(lower=1e-6)
    return conc


def flag_ceo_concentration_trend(conc: pd.DataFrame) -> pd.DataFrame:
    """Flag firms where C_jt rises over time (positive slope)."""
    trends = (
        conc.groupby("isin")["C_jt"]
        .apply(lambda s: np.polyfit(range(len(s)), s.values, 1)[0] if len(s) >= 3 else np.nan)
        .reset_index(name="C_jt_trend")
    )
    threshold = trends["C_jt_trend"].quantile(0.75)
    trends["flag_ceo_concentration"] = trends["C_jt_trend"] >= threshold
    return trends
