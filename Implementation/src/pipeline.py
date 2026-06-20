"""Executive compensation pipeline — guide formulas (Parts 0–6) + fundamental peer clustering."""

from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from config import BASE_YEAR, CPI_BY_YEAR, DATA_DIR, N_PEER_CLUSTERS, OUTPUT_DATA, PAY_BUCKETS
from formulas import (
    annualize_pay,
    compute_ceo_concentration,
    compute_divergence,
    compute_reach,
    count_movers,
    deflate_pay,
    extract_year_effects,
    fit_asymmetric_ratchet,
    fit_median_benchmark,
    fit_secrecy_premium,
    flag_ceo_concentration_trend,
    mobility_event_study,
    treadmill_decomposition,
)

warnings.filterwarnings("ignore", category=FutureWarning)


def _parse_fy_days(series_begin: pd.Series, series_end: pd.Series) -> pd.Series:
    begin = pd.to_datetime(series_begin, format="%d%b%Y", errors="coerce")
    end = pd.to_datetime(series_end, format="%d%b%Y", errors="coerce")
    return (end - begin).dt.days


def load_orbis() -> pd.DataFrame:
    orbis = pd.read_csv(DATA_DIR / "ORBIS_Abzug_DE_2005_2024.csv", low_memory=False)
    orbis = orbis.rename(columns={"SD_ISIN": "isin", "CLOSDATE_year": "year"})
    orbis = orbis[orbis["isin"].notna()].copy()
    cols = ["isin", "year", "OPRE", "ROA", "GEAR", "TOAS", "ROE", "EMPL", "OPPL", "MAINEXCH", "LISTED"]
    return orbis[cols].sort_values("OPRE", ascending=False).drop_duplicates(["isin", "year"], keep="first")


def step1_clean_and_join() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    """Part 0 — Formulas (1) and (2): annualize, deflate, build XF and XP."""
    board = pd.read_csv(DATA_DIR / "2008-2020/company_year.csv", sep="|")
    person = pd.read_csv(DATA_DIR / "2008-2020/person_year.csv", sep="|")
    links = pd.read_csv(DATA_DIR / "2008-2020/company_person.csv", sep="|")
    orbis = load_orbis()

    xf = board.merge(orbis, on=["isin", "year"], how="left")
    xp = person.merge(orbis, on=["isin", "year"], how="left")

    # Formula (1): L_it from fy_begin/fy_end; d_it = days_bt [BOARD] or days [PERSON]
    xf["L_it"] = _parse_fy_days(xf["fy_begin"], xf["fy_end"])
    xf["pay_ann"] = annualize_pay(xf["total_comp_bt"], xf["L_it"], xf["days_bt"])

    for label, col in PAY_BUCKETS.items():
        if col in xf.columns:
            xf[f"{label}_ann"] = annualize_pay(xf[col].fillna(0), xf["L_it"], xf["days_bt"])

    fy_lookup = xf[["isin", "year", "L_it"]].drop_duplicates()
    xp = xp.merge(fy_lookup, on=["isin", "year"], how="left")
    xp["L_it"] = xp["L_it"].fillna(365)
    xp["pay_ann"] = annualize_pay(xp["total_comp"], xp["L_it"], xp["days"])

    # Formula (2): deflate to real euros, base year t*
    cpi = pd.DataFrame({"year": list(CPI_BY_YEAR.keys()), "cpi": list(CPI_BY_YEAR.values())})
    base_cpi = CPI_BY_YEAR[BASE_YEAR]
    xf = xf.merge(cpi, on="year", how="left")
    xp = xp.merge(cpi, on="year", how="left")
    xf["pay_real"] = deflate_pay(xf["pay_ann"], xf["cpi"], base_cpi)
    xp["pay_real"] = deflate_pay(xp["pay_ann"], xp["cpi"], base_cpi)

    for label in PAY_BUCKETS:
        ann_col = f"{label}_ann"
        if ann_col in xf.columns:
            xf[f"{label}_real"] = deflate_pay(xf[ann_col], xf["cpi"], base_cpi)

    xf_clean = xf.dropna(subset=["OPRE", "ROA", "GEAR", "pay_real"]).copy()
    xf_clean = xf_clean[(xf_clean["OPRE"] > 0) & (xf_clean["pay_real"] > 0)]
    xf_clean["turnover_per_empl"] = xf_clean["OPRE"] / xf_clean["EMPL"].clip(lower=1)

    mover_stats = count_movers(links)
    stats = {
        "board_rows": len(board),
        "person_rows": len(person),
        "join_rate": float(xf["OPRE"].notna().mean()),
        "usable_firm_years": len(xf_clean),
        "usable_firms": int(xf_clean["isin"].nunique()),
        "years_min": int(xf_clean["year"].min()),
        "years_max": int(xf_clean["year"].max()),
        "movers": int(mover_stats["is_mover"].sum()),
        "cpi_base_year": BASE_YEAR,
    }

    xf_clean.to_parquet(OUTPUT_DATA / "xf_clean.parquet", index=False)
    xp.to_parquet(OUTPUT_DATA / "xp.parquet", index=False)
    links.to_parquet(OUTPUT_DATA / "links.parquet", index=False)
    pd.DataFrame([stats]).to_csv(OUTPUT_DATA / "step1_stats.csv", index=False)

    return xf_clean, xp, links, stats


def _build_firm_cluster_features(xf: pd.DataFrame) -> pd.DataFrame:
    firm = (
        xf.groupby("isin")
        .agg(
            median_toas=("TOAS", "median"),
            turnover_per_empl=("turnover_per_empl", "median"),
            median_empl=("EMPL", "median"),
            median_oppl=("OPPL", "median"),
            median_opre=("OPRE", "median"),
            roa=("ROA", "median"),
            gear=("GEAR", "median"),
            n_years=("year", "count"),
            median_pay=("pay_real", "median"),
        )
        .reset_index()
    )
    firm["log_toas"] = np.log(firm["median_toas"].clip(lower=1))
    firm["log_empl"] = np.log(firm["median_empl"].clip(lower=1))
    firm["log_oppl"] = np.log(firm["median_oppl"].clip(lower=1))
    firm["log_opre"] = np.log(firm["median_opre"].clip(lower=1))
    return firm


def _select_cluster_k(X: np.ndarray, n_firms: int) -> int:
    k_min, k_max = 4, min(10, max(5, n_firms // 12))
    if n_firms < 8:
        return max(2, n_firms // 2)
    best_k, best_score = k_min, -1.0
    for k in range(k_min, k_max + 1):
        if k >= n_firms:
            break
        labels = KMeans(n_clusters=k, random_state=42, n_init=20).fit_predict(X)
        if len(set(labels)) < 2:
            continue
        score = silhouette_score(X, labels)
        if score > best_score:
            best_k, best_score = k, score
    return best_k


def step2_cluster_peers(xf: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Peer groups for benchmarking (clustering on TOAS, turnover/EMPL, EMPL, OPPL, OPRE, ROA, GEAR)."""
    firm = _build_firm_cluster_features(xf)
    feature_cols = ["log_toas", "turnover_per_empl", "log_empl", "log_oppl", "log_opre", "roa", "gear"]
    X_raw = firm[feature_cols].fillna(firm[feature_cols].median())
    scaler = StandardScaler()
    X = scaler.fit_transform(X_raw)

    k = min(N_PEER_CLUSTERS, len(firm))
    kmeans = KMeans(n_clusters=k, random_state=42, n_init=20)
    firm["peer_cluster"] = kmeans.fit_predict(X)
    firm["peer_label"] = firm["peer_cluster"].apply(lambda c: f"Peer_C{int(c)}")

    # Company names from board data (modal name per ISIN)
    names = (
        xf.groupby("isin")
        .agg(
            company_shortname=("company_shortname", lambda x: x.mode().iloc[0] if len(x.mode()) else x.iloc[0]),
            company_name=("company_name", lambda x: x.mode().iloc[0] if len(x.mode()) else x.iloc[0]),
            index_listing=("index_listing", lambda x: x.mode().iloc[0] if len(x.mode()) else None),
        )
        .reset_index()
    )
    firm = firm.merge(names, on="isin", how="left")

    xf = xf.merge(firm[["isin", "peer_cluster", "peer_label"]], on="isin", how="left")

    # Dataset: every company with its peer cluster
    peer_companies = firm[
        [
            "peer_label",
            "peer_cluster",
            "isin",
            "company_shortname",
            "company_name",
            "index_listing",
            "n_years",
            "median_opre",
            "median_toas",
            "median_empl",
            "median_oppl",
            "turnover_per_empl",
            "roa",
            "gear",
            "median_pay",
        ]
    ].sort_values(["peer_label", "company_shortname"])
    peer_companies.to_csv(OUTPUT_DATA / "peer_cluster_companies.csv", index=False)

    # Firm-year level: company name + cluster for each year in sample
    peer_firm_years = xf[
        [
            "peer_label",
            "peer_cluster",
            "isin",
            "year",
            "company_shortname",
            "company_name",
            "index_listing",
            "OPRE",
            "TOAS",
            "EMPL",
            "OPPL",
            "ROA",
            "GEAR",
            "pay_real",
        ]
    ].sort_values(["peer_label", "company_shortname", "year"])
    peer_firm_years.to_csv(OUTPUT_DATA / "peer_cluster_firm_years.csv", index=False)

    profile = (
        xf.groupby("peer_label")
        .agg(
            n_firms=("isin", "nunique"),
            n_firm_years=("year", "count"),
            median_toas=("TOAS", "median"),
            median_turnover_per_empl=("turnover_per_empl", "median"),
            median_empl=("EMPL", "median"),
            median_oppl=("OPPL", "median"),
            median_opre=("OPRE", "median"),
            median_roa=("ROA", "median"),
            median_gear=("GEAR", "median"),
            median_pay=("pay_real", "median"),
        )
        .reset_index()
        .sort_values("n_firm_years", ascending=False)
    )

    cluster_roster = peer_companies.groupby("peer_label").apply(
        lambda g: "; ".join(
            f"{row['company_shortname']} ({row['isin']})"
            for _, row in g.sort_values("company_shortname").iterrows()
        ),
        include_groups=False,
    ).reset_index(name="companies")
    cluster_roster = cluster_roster.merge(
        profile[["peer_label", "n_firms", "n_firm_years"]],
        on="peer_label",
    )
    cluster_roster.to_csv(OUTPUT_DATA / "peer_cluster_roster.csv", index=False)

    centroids = pd.DataFrame(
        scaler.inverse_transform(kmeans.cluster_centers_),
        columns=feature_cols,
    )
    centroids["peer_label"] = [f"Peer_C{i}" for i in range(k)]
    centroids.to_csv(OUTPUT_DATA / "cluster_centroids.csv", index=False)
    firm.to_parquet(OUTPUT_DATA / "peer_firms.parquet", index=False)
    xf.to_parquet(OUTPUT_DATA / "xf_with_peers.parquet", index=False)
    profile.to_csv(OUTPUT_DATA / "peer_cluster_profile.csv", index=False)
    return xf, profile


def step3_benchmark(xf: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Part 1 — Formulas (3) and (4): median benchmark within each peer cluster."""
    results, model_rows = [], []

    for label in xf["peer_label"].dropna().unique():
        sub = xf[xf["peer_label"] == label]
        if len(sub) < 10:
            continue
        fitted, params = fit_median_benchmark(sub, y_col="pay_real", peer_label=label)
        results.append(fitted)
        model_rows.append(params)

    if not results:
        fitted, params = fit_median_benchmark(xf, y_col="pay_real", peer_label="ALL")
        results = [fitted]
        model_rows = [params]

    xf_bench = pd.concat(results, ignore_index=True)
    xf_bench["peer_rank"] = xf_bench.groupby("peer_label")["residual"].rank(pct=True)
    xf_bench["peer_status"] = pd.cut(
        xf_bench["peer_rank"],
        bins=[0, 0.25, 0.75, 1.0],
        labels=["below_peers", "in_line", "above_peers"],
        include_lowest=True,
    )

    models = pd.DataFrame(model_rows)
    xf_bench.to_parquet(OUTPUT_DATA / "xf_benchmark.parquet", index=False)
    models.to_csv(OUTPUT_DATA / "benchmark_models.csv", index=False)
    return xf_bench, models


from ozkan import run_ozkan_pipeline


def step3_ozkan(xf: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Ozkan (2011) Eq. 6.1 — predict total/cash/LTI comp within peer clusters."""
    return run_ozkan_pipeline(xf)


def step4_reach(xf: pd.DataFrame) -> pd.DataFrame:
    """Part 2 — Formulas (5) and (6): reach = exp(epsilon/beta) = S_phantom / OPRE."""
    xf = compute_reach(xf)
    xf["flag_excessive"] = xf.groupby("peer_label")["reach"].transform(lambda s: s >= s.quantile(0.90))

    reach_summary = (
        xf.groupby("peer_label")
        .agg(
            median_reach=("reach", "median"),
            p90_reach=("reach", lambda s: s.quantile(0.9)),
            n_excessive=("flag_excessive", "sum"),
        )
        .reset_index()
    )
    reach_summary.to_csv(OUTPUT_DATA / "reach_summary.csv", index=False)
    xf.to_parquet(OUTPUT_DATA / "xf_reach.parquet", index=False)
    return xf


def step5_buckets(xf: pd.DataFrame) -> pd.DataFrame:
    """Part 3 — Formula (8): reach^(b) = exp(epsilon^(b)/beta_b); D_it = Var_b(log reach^(b))."""
    xf = xf.copy()
    reach_cols = []

    for bname in PAY_BUCKETS:
        real_col = f"{bname}_real"
        if real_col not in xf.columns:
            continue
        bucket_parts = []
        for label in xf["peer_label"].dropna().unique():
            sub = xf[(xf["peer_label"] == label) & (xf[real_col] > 0)]
            if len(sub) < 8:
                continue
            fitted, params = fit_median_benchmark(sub, y_col=real_col, peer_label=f"{label}_{bname}")
            fitted = fitted[["isin", "year", "residual", "beta"]].rename(columns={"residual": f"eps_{bname}"})
            fitted[f"beta_{bname}"] = params["beta"]
            bucket_parts.append(fitted)

        if not bucket_parts:
            continue

        merged = pd.concat(bucket_parts, ignore_index=True)
        beta_b = merged[f"beta_{bname}"].replace(0, np.nan).fillna(0.3)
        merged[f"reach_{bname}"] = np.exp(merged[f"eps_{bname}"] / beta_b)
        xf = xf.merge(merged[["isin", "year", f"reach_{bname}"]], on=["isin", "year"], how="left")
        reach_cols.append(f"reach_{bname}")

    if reach_cols:
        xf["divergence"] = compute_divergence(xf, reach_cols)
        xf["flag_hidden_stretch"] = xf["divergence"] >= xf["divergence"].quantile(0.90)

    xf.to_parquet(OUTPUT_DATA / "xf_buckets.parquet", index=False)
    return xf


def step6_treadmill(models: pd.DataFrame, xf: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Part 4 — Route A: delta_t series; Route B: Formula (9) decomposition."""
    route_a = extract_year_effects(models)
    route_a.to_csv(OUTPUT_DATA / "treadmill_route_a.csv", index=False)

    year_first = int(xf["year"].min())
    year_last = int(xf["year"].max())
    decomp = treadmill_decomposition(xf, year_first, year_last)
    decomp_df = pd.DataFrame([decomp]) if decomp else pd.DataFrame()
    if len(decomp_df):
        decomp_df.to_csv(OUTPUT_DATA / "treadmill_route_b.csv", index=False)

    route_a.to_csv(OUTPUT_DATA / "treadmill.csv", index=False)
    return route_a, decomp_df


def step7_mobility(xp: pd.DataFrame, links: pd.DataFrame, xf: pd.DataFrame) -> pd.DataFrame:
    """Part 5 — Formulas (10) and (11): movers and event-study tau_k."""
    mover_counts = count_movers(links)
    mover_ids = mover_counts.loc[mover_counts["is_mover"], "exec_id"]
    mover_counts.to_csv(OUTPUT_DATA / "mover_counts.csv", index=False)

    events, tau = mobility_event_study(xp, xf, mover_ids)
    events.to_csv(OUTPUT_DATA / "mobility_events.csv", index=False)
    tau.to_csv(OUTPUT_DATA / "mobility_agg.csv", index=False)
    return tau


def step8_red_flags(xf: pd.DataFrame, xp: pd.DataFrame) -> pd.DataFrame:
    """Part 6 — Formulas (13), (14), (15) plus flags from Parts 2–3 and 5."""
    xf = xf.copy()

    # Formula (13): asymmetric ratchet
    ratchet = fit_asymmetric_ratchet(xf)
    pd.DataFrame([ratchet]).to_csv(OUTPUT_DATA / "ratchet_model.csv", index=False)
    xf = xf.sort_values(["isin", "year"])
    xf["dlog_pay"] = xf.groupby("isin")["pay_real"].transform(lambda s: np.log(s.clip(lower=1)).diff())
    xf["droa"] = xf.groupby("isin")["ROA"].diff()
    xf["flag_ratchet"] = ratchet.get("flag_ratchet", False)

    # Formula (14): secrecy premium
    secrecy = fit_secrecy_premium(xf)
    pd.DataFrame([secrecy]).to_csv(OUTPUT_DATA / "secrecy_model.csv", index=False)
    xf["flag_secrecy"] = (xf["opting_out"] == 1) & (xf["reach"] > xf["reach"].median())
    if secrecy.get("flag_secrecy_premium"):
        xf.loc[xf["opting_out"] == 1, "flag_secrecy"] = True

    # Formula (15): CEO concentration C_jt
    conc = compute_ceo_concentration(xp)
    conc.to_csv(OUTPUT_DATA / "ceo_concentration.csv", index=False)
    conc_trends = flag_ceo_concentration_trend(conc)
    xf = xf.merge(conc_trends, on="isin", how="left")

    if "flag_hidden_stretch" not in xf.columns:
        xf["flag_hidden_stretch"] = False

    xf["flag_portable_rent"] = False  # set below if mobility data available

    xf["flag_count"] = (
        xf["flag_excessive"].astype(int)
        + xf["flag_hidden_stretch"].fillna(False).astype(int)
        + xf["flag_secrecy"].astype(int)
        + xf["flag_ceo_concentration"].fillna(False).astype(int)
        + xf["flag_ratchet"].astype(int)
    )

    flags = xf[
        [
            "isin", "year", "company_shortname", "index_listing", "peer_label",
            "pay_real", "reach", "reach_phantom", "divergence", "peer_status",
            "flag_excessive", "flag_hidden_stretch", "flag_secrecy",
            "flag_ceo_concentration", "flag_ratchet", "flag_count",
        ]
    ].copy()

    flags.to_parquet(OUTPUT_DATA / "red_flags.parquet", index=False)
    flags.to_csv(OUTPUT_DATA / "red_flags.csv", index=False)
    xf.to_parquet(OUTPUT_DATA / "xf_final.parquet", index=False)
    return flags


def run_all() -> dict:
    OUTPUT_DATA.mkdir(parents=True, exist_ok=True)
    xf, xp, links, stats = step1_clean_and_join()
    xf, profile = step2_cluster_peers(xf)
    xf, models = step3_benchmark(xf)
    ozkan_params, ozkan_fitted, ozkan_next = step3_ozkan(xf)
    xf = step4_reach(xf)
    xf = step5_buckets(xf)
    treadmill_a, treadmill_b = step6_treadmill(models, xf)
    mobility = step7_mobility(xp, links, xf)
    flags = step8_red_flags(xf, xp)
    return {
        "stats": stats,
        "xf": xf,
        "xp": xp,
        "profile": profile,
        "models": models,
        "ozkan_params": ozkan_params,
        "ozkan_fitted": ozkan_fitted,
        "ozkan_next": ozkan_next,
        "treadmill": treadmill_a,
        "treadmill_b": treadmill_b,
        "mobility": mobility,
        "flags": flags,
    }
