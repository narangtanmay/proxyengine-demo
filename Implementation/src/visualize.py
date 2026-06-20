"""Generate visualization for each pipeline step."""

from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from matplotlib.gridspec import GridSpec

from config import CLUSTER_FEATURE_LABELS, OUTPUT_DATA, OUTPUT_FIGURES

plt.style.use("seaborn-v0_8-whitegrid")
sns.set_palette("colorblind")

STEP_META = [
    {"id": 1, "slug": "step1_data_cleaning", "title": "Step 1 — Data Cleaning & Join", "file": "step1_data_cleaning.png"},
    {"id": 2, "slug": "step2_peer_clustering", "title": "Step 2 — Peer Clustering", "file": "step2_peer_clustering.png"},
    {"id": 3, "slug": "step3_benchmark", "title": "Step 3 — Pay Benchmark (Median Regression)", "file": "step3_benchmark.png"},
    {"id": 31, "slug": "step3_ozkan", "title": "Step 3b — Ozkan (2011) Compensation Prediction", "file": "step3_ozkan.png"},
    {"id": 4, "slug": "step4_reach", "title": "Step 4 — Reach (Over/Under-Payment)", "file": "step4_reach.png"},
    {"id": 5, "slug": "step5_pay_buckets", "title": "Step 5 — Pay Bucket Decomposition", "file": "step5_pay_buckets.png"},
    {"id": 6, "slug": "step6_treadmill", "title": "Step 6 — Compensation Treadmill", "file": "step6_treadmill.png"},
    {"id": 7, "slug": "step7_mobility", "title": "Step 7 — Executive Mobility", "file": "step7_mobility.png"},
    {"id": 8, "slug": "step8_red_flags", "title": "Step 8 — Governance Red Flags", "file": "step8_red_flags.png"},
]


def _save(fig, name: str) -> str:
    OUTPUT_FIGURES.mkdir(parents=True, exist_ok=True)
    path = OUTPUT_FIGURES / name
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return str(path)


def plot_step1(stats: dict, xf: pd.DataFrame) -> str:
    fig = plt.figure(figsize=(14, 10))
    gs = GridSpec(2, 2, figure=fig, hspace=0.35, wspace=0.3)

    ax0 = fig.add_subplot(gs[0, 0])
    labels = ["Joined to ORBIS", "Missing ORBIS"]
    joined = stats["board_rows"] * stats["join_rate"]
    missing = stats["board_rows"] - joined
    ax0.pie([joined, missing], labels=labels, autopct="%1.1f%%", startangle=90, colors=["#2ecc71", "#e74c3c"])
    ax0.set_title("ORBIS Join Coverage")

    ax1 = fig.add_subplot(gs[0, 1])
    ax1.bar(
        ["Board rows", "Usable firm-years", "Firms", "Movers"],
        [stats["board_rows"], stats["usable_firm_years"], stats["usable_firms"], stats["movers"]],
        color=["#3498db", "#9b59b6", "#1abc9c", "#e67e22"],
    )
    ax1.set_title("Sample Overview")
    ax1.tick_params(axis="x", rotation=15)

    ax2 = fig.add_subplot(gs[1, 0])
    sample = xf.dropna(subset=["OPRE", "pay_real"]).copy()
    sample["log_opre"] = np.log10(sample["OPRE"])
    sample["log_pay"] = np.log10(sample["pay_real"])
    sns.scatterplot(data=sample, x="log_opre", y="log_pay", hue="index_listing", alpha=0.6, ax=ax2, legend=False)
    ax2.set_xlabel("Log10 Operating Revenue (OPRE)")
    ax2.set_ylabel("Log10 Real Board Pay (€ thousands)")
    ax2.set_title("Size vs Pay (Post-Cleaning Sanity Check)")

    ax3 = fig.add_subplot(gs[1, 1])
    yearly = xf.groupby("year")["pay_real"].median().reset_index()
    ax3.plot(yearly["year"], yearly["pay_real"], marker="o", linewidth=2, color="#2980b9")
    ax3.fill_between(yearly["year"], yearly["pay_real"], alpha=0.2, color="#2980b9")
    ax3.set_xlabel("Year")
    ax3.set_ylabel("Median Real Pay (€ thousands)")
    ax3.set_title("Median Real Board Pay Over Time")

    fig.suptitle("Step 1: Data Integration, Annualization & Inflation Adjustment", fontsize=14, fontweight="bold", y=1.02)
    return _save(fig, "step1_data_cleaning.png")


def plot_step2(xf: pd.DataFrame, profile: pd.DataFrame) -> str:
    fig = plt.figure(figsize=(14, 10))
    gs = GridSpec(2, 2, figure=fig, hspace=0.35, wspace=0.3)

    firm = xf.groupby("isin").agg(
        log_opre=("OPRE", lambda x: np.log(x.median())),
        roa=("ROA", "median"),
        turnover_per_empl=("turnover_per_empl", "median"),
        peer_label=("peer_label", "first"),
    ).reset_index()

    ax0 = fig.add_subplot(gs[0, 0])
    for label in sorted(firm["peer_label"].dropna().unique()):
        sub = firm[firm["peer_label"] == label]
        ax0.scatter(sub["log_opre"], sub["roa"], label=label, alpha=0.75, s=55)
    ax0.set_xlabel("Log(Median OPRE)")
    ax0.set_ylabel("Median ROA")
    ax0.set_title("Peer Clusters: OPRE vs ROA")
    ax0.legend(fontsize=7, loc="best", ncol=2)

    ax1 = fig.add_subplot(gs[0, 1])
    centroids_path = OUTPUT_DATA / "cluster_centroids.csv"
    if centroids_path.exists():
        cent = pd.read_csv(centroids_path).set_index("peer_label")
        feature_cols = [c for c in cent.columns if c in CLUSTER_FEATURE_LABELS]
        cent_norm = cent[feature_cols].copy()
        for col in feature_cols:
            col_vals = cent_norm[col]
            col_range = col_vals.max() - col_vals.min()
            cent_norm[col] = (col_vals - col_vals.min()) / col_range if col_range > 0 else 0.5
        cent_norm.columns = [CLUSTER_FEATURE_LABELS.get(c, c) for c in feature_cols]
        sns.heatmap(cent_norm, annot=True, fmt=".2f", cmap="Blues", ax=ax1)
        ax1.set_title("Cluster Profiles (Normalized Fundamentals)")
    else:
        ax1.text(0.5, 0.5, "Centroids not available", ha="center", va="center", transform=ax1.transAxes)

    ax2 = fig.add_subplot(gs[1, 0])
    if len(profile):
        profile_plot = profile.sort_values("n_firm_years", ascending=True)
        ax2.barh(profile_plot["peer_label"], profile_plot["n_firm_years"], color="#16a085")
        ax2.set_xlabel("Firm-Years in Cluster")
        ax2.set_title("Cluster Sizes (firm-years per cluster)")

    ax3 = fig.add_subplot(gs[1, 1])
    if len(profile) and "median_turnover_per_empl" in profile.columns:
        sns.scatterplot(
            data=profile,
            x="median_turnover_per_empl",
            y="median_pay",
            size="n_firms",
            sizes=(50, 400),
            hue="peer_label",
            legend=False,
            ax=ax3,
        )
        ax3.set_xscale("log")
        ax3.set_xlabel("Median Turnover per Employee (log scale)")
        ax3.set_ylabel("Median Real Pay (€ thousands)")
        ax3.set_title("Clusters: Productivity vs Pay")

    fig.suptitle(
        "Step 2: Fundamental-Based Peer Clustering (TOAS, Turnover/EMPL, EMPL, OPPL, OPRE, ROA, GEAR)",
        fontsize=13,
        fontweight="bold",
        y=1.02,
    )
    return _save(fig, "step2_peer_clustering.png")


def plot_step3(xf: pd.DataFrame, models: pd.DataFrame) -> str:
    fig = plt.figure(figsize=(14, 10))
    gs = GridSpec(2, 2, figure=fig, hspace=0.35, wspace=0.3)

    ax0 = fig.add_subplot(gs[0, 0])
    if "beta" in models.columns and len(models):
        models_sorted = models.sort_values("beta")
        ax0.barh(models_sorted["peer_label"], models_sorted["beta"], color="#34495e")
        ax0.axvline(0.3, color="red", linestyle="--", label="Expected β ≈ 0.3")
        ax0.set_xlabel("Size Elasticity (β)")
        ax0.legend()
        ax0.set_title("Pay–Size Elasticity by Peer Cluster")

    ax1 = fig.add_subplot(gs[0, 1])
    status_counts = xf["peer_status"].value_counts()
    colors = {"below_peers": "#27ae60", "in_line": "#f39c12", "above_peers": "#c0392b"}
    ax1.pie(
        status_counts.values,
        labels=status_counts.index,
        autopct="%1.1f%%",
        colors=[colors.get(str(x), "#95a5a6") for x in status_counts.index],
    )
    ax1.set_title("Peer Comparison Labels")

    ax2 = fig.add_subplot(gs[1, :])
    top_cluster = xf["peer_label"].value_counts().index[0]
    sub = xf[xf["peer_label"] == top_cluster].copy()
    sub["log_opre"] = np.log10(sub["OPRE"])
    sub["log_pay"] = np.log10(sub["pay_real"])
    sub["fitted"] = sub["log_pay"] - sub["residual"]
    ax2.scatter(sub["log_opre"], sub["log_pay"], alpha=0.5, label="Actual", s=30)
    order = sub.sort_values("log_opre")
    ax2.plot(order["log_opre"], order["fitted"], color="red", linewidth=2, label="Benchmark (median fit)")
    ax2.set_xlabel("Log10 OPRE")
    ax2.set_ylabel("Log10 Real Pay")
    ax2.set_title(f"Benchmark Curve — Example Cluster: {top_cluster}")
    ax2.legend()

    fig.suptitle("Step 3: Median Regression Benchmark Within Peer Groups", fontsize=14, fontweight="bold", y=1.02)
    return _save(fig, "step3_benchmark.png")


def plot_step3_ozkan(ozkan_fitted: pd.DataFrame, ozkan_next: pd.DataFrame, ozkan_params: pd.DataFrame) -> str:
    fig = plt.figure(figsize=(14, 10))
    gs = GridSpec(2, 2, figure=fig, hspace=0.35, wspace=0.3)

    ax0 = fig.add_subplot(gs[0, 0])
    if len(ozkan_params):
        total_params = ozkan_params[ozkan_params["y_col"] == "total_direct_real"]
        if len(total_params):
            ax0.barh(total_params["peer_label"], total_params["beta_ln_opre"], color="#2c3e50")
            ax0.set_xlabel("β — ln(OPRE) coefficient (Ozkan size effect)")
            ax0.set_title("Ozkan Eq. 6.1: Size Elasticity by Peer Cluster")

    ax1 = fig.add_subplot(gs[0, 1])
    if len(ozkan_fitted):
        tot = ozkan_fitted[ozkan_fitted["component"] == "total_direct"]
        if len(tot):
            ax1.scatter(tot["actual_comp"], tot["y_hat"], alpha=0.4, s=25)
            mx = max(tot["actual_comp"].max(), tot["y_hat"].max())
            ax1.plot([0, mx], [0, mx], "r--", label="Perfect prediction")
            ax1.set_xlabel("Actual total direct comp (real)")
            ax1.set_ylabel("Predicted (Ozkan model)")
            ax1.set_title("In-Sample: Actual vs Predicted Total Comp")
            ax1.legend()

    ax2 = fig.add_subplot(gs[1, 0])
    if len(ozkan_next):
        wide_path = OUTPUT_DATA / "ozkan_predicted_comp_next_year.csv"
        if wide_path.exists():
            wide = pd.read_csv(wide_path)
            comp_cols = [c for c in ["cash", "lti", "predicted_total_comp"] if c in wide.columns]
            if comp_cols:
                means = wide[comp_cols].mean()
                means.plot(kind="bar", ax=ax2, color=["#3498db", "#9b59b6", "#e74c3c"][: len(means)])
                ax2.set_ylabel("Mean predicted comp (€ thousands)")
                yr = wide["prediction_year"].iloc[0] if "prediction_year" in wide.columns else "t+1"
                ax2.set_title(f"Next-Year ({yr}) Mean Predicted Pay Mix")
                ax2.tick_params(axis="x", rotation=15)

    ax3 = fig.add_subplot(gs[1, 1])
    if len(ozkan_next):
        top = ozkan_next[ozkan_next["component"] == "total_direct"].nlargest(12, "predicted_comp")
        if len(top):
            top["label"] = top["company_shortname"]
            ax3.barh(top["label"], top["predicted_comp"], color="#16a085")
            ax3.set_xlabel("Predicted total direct comp")
            ax3.set_title("Top 12 Next-Year Predictions")
            ax3.invert_yaxis()

    fig.suptitle(
        "Step 3b: Ozkan (2011) Model — Base + STI + LTI → Total Direct Compensation",
        fontsize=13, fontweight="bold", y=1.02,
    )
    return _save(fig, "step3_ozkan.png")


def plot_step4(xf: pd.DataFrame) -> str:
    fig = plt.figure(figsize=(14, 10))
    gs = GridSpec(2, 2, figure=fig, hspace=0.35, wspace=0.3)

    ax0 = fig.add_subplot(gs[0, 0])
    sns.histplot(xf["reach"].clip(0, 5), bins=40, kde=True, ax=ax0, color="#2980b9")
    ax0.axvline(1.0, color="green", linestyle="--", label="Fair (reach=1)")
    ax0.set_xlabel("Reach")
    ax0.legend()
    ax0.set_title("Distribution of Reach")

    ax1 = fig.add_subplot(gs[0, 1])
    tier_reach = xf.groupby("index_listing")["reach"].median().sort_values(ascending=False)
    tier_reach.plot(kind="bar", ax=ax1, color=["#e74c3c", "#3498db", "#2ecc71", "#95a5a6"][: len(tier_reach)])
    ax1.axhline(1.0, color="green", linestyle="--")
    ax1.set_ylabel("Median Reach")
    ax1.set_title("Median Reach by Index Tier")
    ax1.tick_params(axis="x", rotation=20)

    ax2 = fig.add_subplot(gs[1, 0])
    top = xf.nlargest(15, "reach")[["company_shortname", "year", "reach"]]
    top["label"] = top["company_shortname"] + " (" + top["year"].astype(str) + ")"
    ax2.barh(top["label"], top["reach"], color="#c0392b")
    ax2.axvline(1.0, color="green", linestyle="--")
    ax2.set_xlabel("Reach")
    ax2.set_title("Top 15 Firm-Years by Reach")
    ax2.invert_yaxis()

    ax3 = fig.add_subplot(gs[1, 1])
    excessive = xf.groupby("year")["flag_excessive"].mean() * 100
    ax3.bar(excessive.index, excessive.values, color="#e67e22")
    ax3.set_xlabel("Year")
    ax3.set_ylabel("% Flagged Excessive (top 10%)")
    ax3.set_title("Excessive Pay Flags Over Time")

    fig.suptitle("Step 4: Reach — Pay Relative to Peer Benchmark", fontsize=14, fontweight="bold", y=1.02)
    return _save(fig, "step4_reach.png")


def plot_step5(xf: pd.DataFrame) -> str:
    reach_cols = [c for c in xf.columns if c.startswith("reach_") and c != "reach"]
    fig = plt.figure(figsize=(14, 10))
    gs = GridSpec(2, 2, figure=fig, hspace=0.35, wspace=0.3)

    ax0 = fig.add_subplot(gs[0, 0])
    if reach_cols:
        medians = xf[reach_cols].median().sort_values(ascending=False)
        medians.index = [c.replace("reach_", "").replace("_", " ").title() for c in medians.index]
        medians.plot(kind="barh", ax=ax0, color="#8e44ad")
        ax0.axvline(1.0, color="green", linestyle="--")
        ax0.set_xlabel("Median Reach")
        ax0.set_title("Median Reach by Pay Component")

    ax1 = fig.add_subplot(gs[0, 1])
    if "divergence" in xf.columns:
        sns.histplot(xf["divergence"].dropna(), bins=30, kde=True, ax=ax1, color="#d35400")
        ax1.set_xlabel("Divergence (variance of log bucket reach)")
        ax1.set_title("Hidden Stretch — Bucket Divergence")

    ax2 = fig.add_subplot(gs[1, 0])
    if reach_cols:
        comp_share = xf[[c.replace("reach_", "") + "_real" for c in reach_cols if c.replace("reach_", "") + "_real" in xf.columns]]
        if len(comp_share.columns):
            comp_share = comp_share.clip(lower=0)
            totals = comp_share.sum(axis=1).replace(0, np.nan)
            shares = comp_share.div(totals, axis=0).mean()
            shares.index = [c.replace("_real", "").replace("_", " ").title() for c in shares.index]
            shares.plot(kind="pie", autopct="%1.0f%%", ax=ax2)
            ax2.set_ylabel("")
            ax2.set_title("Average Pay Composition")

    ax3 = fig.add_subplot(gs[1, 1])
    if reach_cols and "divergence" in xf.columns:
        high_div = xf.nlargest(10, "divergence")
        melt = high_div.melt(id_vars=["company_shortname", "year"], value_vars=reach_cols, var_name="bucket", value_name="bucket_reach")
        melt["bucket"] = melt["bucket"].str.replace("reach_", "")
        pivot = melt.pivot_table(index="company_shortname", columns="bucket", values="bucket_reach", aggfunc="mean")
        sns.heatmap(pivot.fillna(0).clip(0, 4), annot=True, fmt=".1f", cmap="YlOrRd", ax=ax3)
        ax3.set_title("High-Divergence Firms: Reach by Bucket")

    fig.suptitle("Step 5: Pay Bucket Decomposition & Hidden Stretch", fontsize=14, fontweight="bold", y=1.02)
    return _save(fig, "step5_pay_buckets.png")


def plot_step6(treadmill: pd.DataFrame, xf: pd.DataFrame, treadmill_b: pd.DataFrame | None = None) -> str:
    fig = plt.figure(figsize=(14, 8))
    gs = GridSpec(1, 3, figure=fig, wspace=0.35)

    ax0 = fig.add_subplot(gs[0, 0])
    col = "delta_t" if "delta_t" in treadmill.columns else "year_effect"
    if len(treadmill) and col in treadmill.columns:
        agg = treadmill.groupby("year")[col].mean().reset_index()
        ax0.plot(agg["year"], agg[col], marker="o", linewidth=2, color="#c0392b")
        ax0.fill_between(agg["year"], agg[col], alpha=0.15, color="#c0392b")
        ax0.set_xlabel("Year")
        ax0.set_ylabel("Year effect δ_t (Route A)")
        ax0.set_title("Formula (9) Route A: Benchmark Drift")

    ax1 = fig.add_subplot(gs[0, 1])
    if treadmill_b is not None and len(treadmill_b):
        row = treadmill_b.iloc[0]
        components = ["fundamentals_component", "treadmill_component"]
        labels = ["Fundamentals\nb'₀(ΔZ̄)", "Treadmill\nZ̄'ₜ(bₜ−b₀)"]
        vals = [row.get(c, 0) for c in components]
        colors = ["#3498db", "#e74c3c"]
        ax1.bar(labels, vals, color=colors)
        ax1.axhline(0, color="black", linewidth=0.8)
        share = row.get("treadmill_share", np.nan)
        ax1.set_ylabel("Δ log pay components")
        ax1.set_title(f"Route B: Treadmill share = {share:.0%}" if pd.notna(share) else "Route B Decomposition")
    else:
        ax1.text(0.5, 0.5, "Route B unavailable", ha="center", va="center", transform=ax1.transAxes)

    ax2 = fig.add_subplot(gs[0, 2])
    first_year = xf["year"].min()
    last_year = xf["year"].max()
    first = xf[xf["year"] == first_year]["pay_real"].median()
    last = xf[xf["year"] == last_year]["pay_real"].median()
    growth_pct = (last / first - 1) * 100
    ax2.bar(["First year", "Last year"], [first, last], color=["#3498db", "#e74c3c"])
    ax2.set_ylabel("Median real pay (€ thousands)")
    ax2.set_title(f"Δ pay {first_year}→{last_year}: {growth_pct:.0f}%")

    fig.suptitle("Step 6: Compensation Treadmill — Formulas (9) Route A & B", fontsize=13, fontweight="bold", y=1.02)
    return _save(fig, "step6_treadmill.png")


def plot_step7(mobility: pd.DataFrame, stats: dict) -> str:
    fig = plt.figure(figsize=(14, 8))
    gs = GridSpec(1, 2, figure=fig, wspace=0.3)

    ax0 = fig.add_subplot(gs[0, 0])
    y_col = "tau_k" if "tau_k" in mobility.columns else "mean_reach"
    if len(mobility):
        ax0.bar(mobility["event_t"], mobility[y_col], color="#9b59b6", edgecolor="black")
        ax0.axvline(0, color="red", linestyle="--", label="Job change (t=0)")
        ax0.set_xlabel("Event time k (years from move)")
        ax0.set_ylabel("τ_k — mean reach")
        ax0.set_title("Formula (11): Event Study τ_k Around Job Changes")
        ax0.legend()
    else:
        ax0.text(0.5, 0.5, "Insufficient mobility events", ha="center", va="center", transform=ax0.transAxes)

    ax1 = fig.add_subplot(gs[0, 1])
    ax1.bar(["Total executives", "Movers (M_i>1)"], [1447, stats.get("movers", 0)], color=["#1abc9c", "#e67e22"])
    ax1.set_title("Formula (10): M_i = # firms per exec_id")
    ax1.text(
        0.5, 0.85,
        "Portable rent: reach survives\nemployer change (Part 5)",
        transform=ax1.transAxes, ha="center", fontsize=10,
        bbox=dict(boxstyle="round", facecolor="wheat", alpha=0.5),
    )

    fig.suptitle("Step 7: Executive Mobility — Formulas (10) & (11)", fontsize=13, fontweight="bold", y=1.02)
    return _save(fig, "step7_mobility.png")


def plot_step8(flags: pd.DataFrame) -> str:
    fig = plt.figure(figsize=(14, 10))
    gs = GridSpec(2, 2, figure=fig, hspace=0.35, wspace=0.3)

    ax0 = fig.add_subplot(gs[0, 0])
    flag_cols = ["flag_excessive", "flag_hidden_stretch", "flag_secrecy", "flag_ceo_concentration", "flag_ratchet"]
    available = [c for c in flag_cols if c in flags.columns]
    counts = {c.replace("flag_", "").replace("_", " ").title(): flags[c].sum() for c in available}
    ax0.bar(counts.keys(), counts.values(), color=["#c0392b", "#d35400", "#8e44ad", "#2980b9"][: len(counts)])
    ax0.tick_params(axis="x", rotation=25)
    ax0.set_ylabel("Firm-Years Flagged")
    ax0.set_title("Red Flag Counts by Type")

    ax1 = fig.add_subplot(gs[0, 1])
    if "flag_count" in flags.columns:
        sns.countplot(data=flags, x="flag_count", ax=ax1, palette="Reds_r")
        ax1.set_xlabel("Number of Simultaneous Flags")
        ax1.set_title("Red Flag Intensity Distribution")

    ax2 = fig.add_subplot(gs[1, 0])
    top_flagged = flags.nlargest(12, "flag_count")
    top_flagged["label"] = top_flagged["company_shortname"] + " (" + top_flagged["year"].astype(str) + ")"
    ax2.barh(top_flagged["label"], top_flagged["reach"], color="#e74c3c")
    ax2.set_xlabel("Reach")
    ax2.set_title("Most Flagged Firm-Years (by reach)")
    ax2.invert_yaxis()

    ax3 = fig.add_subplot(gs[1, 1])
    if "opting_out" in flags.columns or "flag_secrecy" in flags.columns:
        secrecy = flags.groupby("flag_secrecy")["reach"].median() if "flag_secrecy" in flags.columns else None
        if secrecy is not None and len(secrecy):
            secrecy.index = ["Disclosed", "Secrecy + High Reach"]
            secrecy.plot(kind="bar", ax=ax3, color=["#2ecc71", "#c0392b"])
            ax3.axhline(1.0, color="green", linestyle="--")
            ax3.set_ylabel("Median Reach")
            ax3.set_title("Secrecy Premium Check")
            ax3.tick_params(axis="x", rotation=0)

    fig.suptitle("Step 8: Red Flags — Formulas (13) Ratchet, (14) Secrecy, (15) CEO Ratio", fontsize=13, fontweight="bold", y=1.02)
    return _save(fig, "step8_red_flags.png")


def generate_all(results: dict) -> list[dict]:
    paths = []
    paths.append({"step": 1, **STEP_META[0], "path": plot_step1(results["stats"], results["xf"])})
    paths.append({"step": 2, **STEP_META[1], "path": plot_step2(results["xf"], results["profile"])})
    paths.append({"step": 3, **STEP_META[2], "path": plot_step3(results["xf"], results["models"])})
    paths.append({
        "step": 31,
        **STEP_META[3],
        "path": plot_step3_ozkan(
            results.get("ozkan_fitted", pd.DataFrame()),
            results.get("ozkan_next", pd.DataFrame()),
            results.get("ozkan_params", pd.DataFrame()),
        ),
    })
    paths.append({"step": 4, **STEP_META[4], "path": plot_step4(results["xf"])})
    paths.append({"step": 5, **STEP_META[5], "path": plot_step5(results["xf"])})
    paths.append({"step": 6, **STEP_META[6], "path": plot_step6(results["treadmill"], results["xf"], results.get("treadmill_b"))})
    paths.append({"step": 7, **STEP_META[7], "path": plot_step7(results["mobility"], results["stats"])})
    paths.append({"step": 8, **STEP_META[8], "path": plot_step8(results["flags"])})
    pd.DataFrame(paths).to_csv(OUTPUT_DATA / "figure_index.csv", index=False)
    return paths
