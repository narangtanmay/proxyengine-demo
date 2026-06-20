"""
Ozkan (2011) CEO compensation model — adapted to German board data + peer clusters.

Paper: Ozkan (2011), European Financial Management, Eq. 6.1 (level model):
  ln(compensation_it) = η·performance + Σ δk·governance + Σ βj·controls + year FE + ε

Adaptation for this project:
  - Performance proxy: ROA (ORBIS) — shareholder return not in dataset
  - Firm size: ln(OPRE) — maps to ln(Sales) in Ozkan
  - Governance proxies: n_executives (board size), opting_out
  - Peer cluster: separate coefficients per cluster (replaces industry FE)
  - Lagged controls (t-1 → t) per Ozkan endogeneity treatment
  - Total direct comp = salary + STI + LTI (Ozkan Table 1 definition)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import statsmodels.api as sm

from config import OUTPUT_DATA

# Ozkan pay structure mapped to our columns
CASH_COLS = ["salary_real", "one_year_bonus_real"]
LTI_COLS = ["stock_grants_real", "option_grants_real", "multi_year_grants_real"]


def build_ozkan_pay_components(xf: pd.DataFrame) -> pd.DataFrame:
    """Build Ozkan-style cash, LTI, and total direct compensation (real)."""
    df = xf.copy()
    for cols, name in [(CASH_COLS, "cash_real"), (LTI_COLS, "lti_real")]:
        available = [c for c in cols if c in df.columns]
        df[name] = df[available].sum(axis=1) if available else np.nan
    df["total_direct_real"] = df["cash_real"].fillna(0) + df["lti_real"].fillna(0)
    # Prefer total_comp_real if buckets incomplete
    if "pay_real" in df.columns:
        mask = df["total_direct_real"] <= 0
        df.loc[mask, "total_direct_real"] = df.loc[mask, "pay_real"]
    return df


def _add_lags(df: pd.DataFrame) -> pd.DataFrame:
    df = df.sort_values(["isin", "year"]).copy()
    lag_cols = ["OPRE", "ROA", "GEAR", "n_executives", "opting_out"]
    for col in lag_cols:
        if col in df.columns:
            df[f"{col}_lag1"] = df.groupby("isin")[col].shift(1)
    return df


def fit_ozkan_level_model(
    df: pd.DataFrame,
    y_col: str,
    peer_label: str,
    min_obs: int = 15,
) -> tuple[dict | None, pd.DataFrame]:
    """
    Ozkan Eq. 6.1 (adapted) within peer cluster:
      ln(y) = α + η·ROA_{t-1} + β·ln(OPRE_{t-1}) + γ·GEAR_{t-1}
              + θ·BoardSize_{t-1} + ρ·opting_out_{t-1} + δ_t + ε
    """
    sub = df[(df["peer_label"] == peer_label) & (df[y_col] > 0)].copy()
    sub = sub.dropna(subset=[f"{c}_lag1" for c in ["OPRE", "ROA", "GEAR"] if f"{c}_lag1" in sub.columns])
    sub["ln_y"] = np.log(sub[y_col].clip(lower=1e-6))
    sub["ln_opre_lag"] = np.log(sub["OPRE_lag1"].clip(lower=1e-6))

    if len(sub) < min_obs:
        return None, sub

    x_parts = [sub[["ln_opre_lag", "ROA_lag1", "GEAR_lag1"]]]
    if "n_executives_lag1" in sub.columns:
        x_parts.append(sub[["n_executives_lag1"]].rename(columns={"n_executives_lag1": "board_size_lag"}))
    if "opting_out_lag1" in sub.columns:
        x_parts.append(sub[["opting_out_lag1"]])

    year_dum = pd.get_dummies(sub["year"].astype(int), prefix="yr", drop_first=True)
    X = sm.add_constant(pd.concat(x_parts + [year_dum], axis=1)).astype(float)
    y = sub["ln_y"].astype(float)

    try:
        model = sm.OLS(y, X).fit()
    except Exception:
        return None, sub

    params = {
        "peer_label": peer_label,
        "y_col": y_col,
        "n": int(model.nobs),
        "r2": float(model.rsquared),
        "alpha": float(model.params.get("const", np.nan)),
        "eta_roa": float(model.params.get("ROA_lag1", np.nan)),
        "beta_ln_opre": float(model.params.get("ln_opre_lag", np.nan)),
        "gamma_gear": float(model.params.get("GEAR_lag1", np.nan)),
        "theta_board": float(model.params.get("board_size_lag", np.nan)) if "board_size_lag" in model.params else np.nan,
        "rho_opting_out": float(model.params.get("opting_out_lag1", np.nan)) if "opting_out_lag1" in model.params else np.nan,
    }
    for col in model.params.index:
        if col.startswith("yr_"):
            params[col] = float(model.params[col])

    sub["ln_y_hat"] = model.predict(X)
    sub["y_hat"] = np.exp(sub["ln_y_hat"])
    sub["residual_ln"] = sub["ln_y"] - sub["ln_y_hat"]
    return params, sub


def predict_next_year(
    df: pd.DataFrame,
    params: dict,
    target_year: int,
    y_col: str = "total_direct_real",
) -> pd.DataFrame:
    """Predict compensation for target_year using lagged fundamentals from target_year - 1."""
    prev = target_year - 1
    base = df[df["year"] == prev].copy()
    if not len(base):
        return pd.DataFrame()

    pred = base[["isin", "company_shortname", "peer_label", "year"]].copy()
    pred["fundamental_year"] = prev
    pred["prediction_year"] = target_year

    ln_opre = np.log(base["OPRE"].clip(lower=1e-6))
    ln_hat = (
        params.get("alpha", 0)
        + params.get("beta_ln_opre", 0) * ln_opre
        + params.get("eta_roa", 0) * base["ROA"].fillna(0)
        + params.get("gamma_gear", 0) * base["GEAR"].fillna(0)
    )
    if "n_executives" in base.columns and not np.isnan(params.get("theta_board", np.nan)):
        ln_hat = ln_hat + params["theta_board"] * base["n_executives"].fillna(0)
    if "opting_out" in base.columns and not np.isnan(params.get("rho_opting_out", np.nan)):
        ln_hat = ln_hat + params["rho_opting_out"] * base["opting_out"].fillna(0)

    yr_key = f"yr_{target_year}"
    if yr_key in params:
        ln_hat = ln_hat + params[yr_key]
    elif f"yr_{prev}" in params:
        # Extrapolate: use last year effect if target year dummy not estimated
        ln_hat = ln_hat + params[f"yr_{prev}"]

    pred["predicted_ln_comp"] = ln_hat
    pred["predicted_comp"] = np.exp(ln_hat)
    pred["component"] = y_col.replace("_real", "")

    if y_col in base.columns:
        pred["actual_comp_lag_year"] = base[y_col].values
    return pred


def run_ozkan_pipeline(xf: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Fit Ozkan models per peer cluster; predict in-sample and next-year."""
    df = build_ozkan_pay_components(xf)
    df = _add_lags(df)

    components = {
        "total_direct_real": "total_direct",
        "cash_real": "cash",
        "lti_real": "lti",
    }

    all_params = []
    all_fitted = []
    all_next = []

    last_year = int(df["year"].max())
    next_year = last_year + 1

    for y_col, label in components.items():
        if y_col not in df.columns:
            continue
        for peer in df["peer_label"].dropna().unique():
            params, fitted = fit_ozkan_level_model(df, y_col, peer)
            if params is None:
                continue
            params["component_label"] = label
            all_params.append(params)
            fitted = fitted.copy()
            fitted["component"] = label
            fitted["actual_comp"] = fitted[y_col]
            all_fitted.append(
                fitted[
                    ["isin", "year", "company_shortname", "peer_label", "component",
                     "actual_comp", "y_hat", "residual_ln"]
                ]
            )
            nxt = predict_next_year(df[df["peer_label"] == peer], params, next_year, y_col)
            if len(nxt):
                all_next.append(nxt)

    params_df = pd.DataFrame(all_params)
    fitted_df = pd.concat(all_fitted, ignore_index=True) if all_fitted else pd.DataFrame()
    next_df = pd.concat(all_next, ignore_index=True) if all_next else pd.DataFrame()

    if len(params_df):
        params_df.to_csv(OUTPUT_DATA / "ozkan_model_coefficients.csv", index=False)
    if len(fitted_df):
        fitted_df.to_csv(OUTPUT_DATA / "ozkan_insample_predictions.csv", index=False)
    if len(next_df):
        # Pivot components to wide format for challenge deliverable
        wide = next_df.pivot_table(
            index=["isin", "company_shortname", "peer_label", "fundamental_year", "prediction_year"],
            columns="component",
            values="predicted_comp",
            aggfunc="first",
        ).reset_index()
        wide.columns.name = None
        if "total_direct" in wide.columns:
            wide["predicted_total_comp"] = wide["total_direct"]
        elif "cash" in wide.columns and "lti" in wide.columns:
            wide["predicted_total_comp"] = wide["cash"].fillna(0) + wide["lti"].fillna(0)
        wide.to_csv(OUTPUT_DATA / "ozkan_predicted_comp_next_year.csv", index=False)
        next_df.to_csv(OUTPUT_DATA / "ozkan_predicted_comp_long.csv", index=False)

    return params_df, fitted_df, next_df


def list_companies(xf: pd.DataFrame | None = None) -> pd.DataFrame:
    """Return sortable company roster (isin, name, peer_label, index)."""
    if xf is not None:
        latest = (
            xf.sort_values("year")
            .groupby("isin", as_index=False)
            .tail(1)[["isin", "company_shortname", "peer_label", "index_listing"]]
        )
        return latest.sort_values("company_shortname")
    path = OUTPUT_DATA / "peer_cluster_companies.csv"
    if path.exists():
        df = pd.read_csv(path)[["isin", "company_shortname", "peer_label", "index_listing"]]
        return df.sort_values("company_shortname")
    return pd.DataFrame(columns=["isin", "company_shortname", "peer_label", "index_listing"])


def _resolve_company(df: pd.DataFrame, company_key: str) -> pd.DataFrame:
    key = company_key.strip()
    if key.startswith("DE") and len(key) >= 10:
        hit = df[df["isin"] == key]
        if len(hit):
            return hit
    hit = df[df["company_shortname"].str.lower() == key.lower()]
    if len(hit):
        return hit
    return df[df["company_shortname"].str.contains(key, case=False, na=False)]


def predict_single_company(
    xf: pd.DataFrame,
    company_key: str,
    params_df: pd.DataFrame | None = None,
) -> dict:
    """Predict next-year cash, LTI, and total comp for one company."""
    df = build_ozkan_pay_components(xf)
    df = _add_lags(df)
    firm = _resolve_company(df, company_key)
    if firm.empty:
        return {"error": f"Company not found: {company_key}"}

    isin = firm["isin"].iloc[0]
    firm = df[df["isin"] == isin].copy()
    name = firm["company_shortname"].iloc[0]
    last_year = int(df["year"].max())
    next_year = last_year + 1
    latest = firm[firm["year"] == last_year]
    if latest.empty:
        latest = firm.sort_values("year").iloc[[-1]]
    latest = latest.iloc[0]
    peer = latest["peer_label"]

    if params_df is None:
        coeff_path = OUTPUT_DATA / "ozkan_model_coefficients.csv"
        if not coeff_path.exists():
            return {"error": "Run pipeline first (ozkan_model_coefficients.csv missing)."}
        params_df = pd.read_csv(coeff_path)

    components = {
        "total_direct_real": "total_direct",
        "cash_real": "cash",
        "lti_real": "lti",
    }
    preds: dict[str, float] = {}
    for y_col, label in components.items():
        prow = params_df[
            (params_df["peer_label"] == peer) & (params_df["component_label"] == label)
        ]
        if prow.empty:
            continue
        params = prow.iloc[0].to_dict()
        one = predict_next_year(firm, params, next_year, y_col)
        if len(one):
            preds[label] = float(one["predicted_comp"].iloc[0])

    peer_path = OUTPUT_DATA / "peer_cluster_companies.csv"
    peer_median_pay = None
    if peer_path.exists():
        peers = pd.read_csv(peer_path)
        prow = peers[peers["isin"] == isin]
        if len(prow):
            peer_median_pay = float(prow.iloc[0].get("median_pay", np.nan))

    cash_act = float(latest.get("cash_real", np.nan))
    lti_act = float(latest.get("lti_real", np.nan))
    total_act = float(latest.get("total_direct_real", latest.get("pay_real", np.nan)))

    total_pred = preds.get("total_direct")
    if total_pred is None and preds:
        total_pred = preds.get("cash", 0) + preds.get("lti", 0)

    return {
        "isin": isin,
        "company": name,
        "peer_label": peer,
        "index_listing": latest.get("index_listing") or "—",
        "fundamental_year": last_year,
        "prediction_year": next_year,
        "fundamentals": {
            "opre_m": round(float(latest.get("OPRE", 0)) / 1e6, 1),
            "roa_pct": round(float(latest.get("ROA", 0)), 2),
            "gear_pct": round(float(latest.get("GEAR", 0)), 2),
            "board_size": int(latest.get("n_executives", 0)) if pd.notna(latest.get("n_executives")) else "—",
        },
        "actual_last_year": {
            "cash_k": round(cash_act, 0) if pd.notna(cash_act) else None,
            "lti_k": round(lti_act, 0) if pd.notna(lti_act) else None,
            "total_k": round(total_act, 0) if pd.notna(total_act) else None,
        },
        "predicted": {k: round(v, 0) for k, v in preds.items()},
        "predicted_total_k": round(total_pred, 0) if total_pred is not None else None,
        "peer_median_pay_k": round(peer_median_pay, 0) if peer_median_pay and pd.notna(peer_median_pay) else None,
        "formula": "Ozkan (2011) Eq. 6.1 — ln(comp) = α + η·ROA + β·ln(OPRE) + γ·GEAR + governance + year FE",
    }
