"""Presentation figures + ranking table for PRESENTATION.md.

Generates 13 self-contained, plain-language figures (PNG) into
build/figures/presentation/ and injects the red-flag ranking table into
PRESENTATION.md (replacing the <!-- TABLE:redflag_ranking --> marker).

Run:  python -m src.present
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from . import config as cfg
from . import (part0_clean, part1_benchmark, part2_reach, part3_buckets,
               part4_treadmill, part6_redflags)

FIG = cfg.BUILD_DIR / "figures" / "presentation"
FIG.mkdir(parents=True, exist_ok=True)

BLUE, ORANGE, RED, GREY = "#2b6cb0", "#d97706", "#aa1e1e", "#666666"
BUCKET_COL = {"Fixed": BLUE, "STI": ORANGE, "LTI": RED}


def _style():
    plt.rcParams.update({
        "figure.dpi": 110, "savefig.dpi": 200, "font.size": 12,
        "axes.titlesize": 12.5, "axes.titleweight": "bold",
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.alpha": 0.25, "axes.axisbelow": True,
        "figure.autolayout": True,
    })


def _save(fig, name):
    p = FIG / f"{name}.png"
    fig.savefig(p)
    plt.close(fig)
    return p


# --------------------------------------------------------------------------- #
def _data():
    fy = part0_clean.build_firm_year()
    py = part0_clean.build_person_year()
    fit = part1_benchmark.fit_benchmark(fy)                       # real pay
    fit_nom = part1_benchmark.fit_benchmark(fy, pay_col="total_comp_bt")  # nominal
    reach = part2_reach.reach_from_benchmark(fit)                 # has premium + reach
    b3 = part3_buckets.fit_bucket_reach(fy, "3")
    hidden = part3_buckets.hidden_stretch(b3["reach_long"], reach)
    ta = part4_treadmill.route_a(fit)
    ta_nom = part4_treadmill.route_a(fit_nom)
    ratchet = part6_redflags.asymmetric_ratchet(fy)
    secrecy = part6_redflags.secrecy_premium(reach, fy)
    conc = part6_redflags.internal_concentration(py)
    ranking = part6_redflags.redflag_ranking(fy, reach, hidden, conc["by_year"])
    return dict(fy=fy, py=py, fit=fit, fit_nom=fit_nom, reach=reach, b3=b3,
                hidden=hidden, ta=ta, ta_nom=ta_nom, ratchet=ratchet,
                secrecy=secrecy, conc=conc, ranking=ranking)


# ---- 01 panel coverage ---------------------------------------------------- #
def fig01(d):
    _style()
    fy = d["fy"]
    n = fy[fy["total_comp_bt"] > 0].groupby("year")["isin"].nunique()
    fig, ax = plt.subplots(figsize=(7, 3.6))
    ax.bar(n.index, n.values, color=BLUE, alpha=0.85)
    ax.set_xlabel("year"); ax.set_ylabel("firms observed")
    ax.set_title("How many firms we observe each year")
    return _save(fig, "01_panel_coverage")


# ---- 02 reconciliation ---------------------------------------------------- #
def fig02(d):
    _style()
    py, fy = d["py"], d["fy"]
    ps = py.groupby(["isin", "year"])["total_comp"].sum().rename("person")
    bt = fy.set_index(["isin", "year"])["total_comp_bt"].rename("board")
    m = pd.concat([bt, ps], axis=1).dropna()
    m = m[(m["board"] > 0) & (m["person"] > 0)]
    fig, ax = plt.subplots(figsize=(6.0, 5.0))
    ax.scatter(m["board"], m["person"], s=10, alpha=0.4, color=BLUE, edgecolors="none")
    lim = [m.values.min() * 0.8, m.values.max() * 1.2]
    ax.plot(lim, lim, color=RED, lw=1.3, ls="--", label="exact match")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("board total pay, reported  (1000€)")
    ax.set_ylabel("sum of individual executives' pay  (1000€)")
    ax.set_title("Data check: the two pay sources agree")
    ax.legend(frameon=False)
    return _save(fig, "02_reconciliation")


# ---- 03 benchmark fit (the peer line) ------------------------------------- #
def fig03(d):
    _style()
    fit = d["fit"]; fr = fit["frame"].copy()
    fr["reach"] = np.exp(fr["eps"] / fit["beta"])
    p = fit["model"].params
    roa_med, gear_med = fr["roa"].median(), fr["gear"].median()
    grid = np.logspace(np.log10(fr["opre"].min()), np.log10(fr["opre"].max()), 100)
    line = np.exp(p["Intercept"] + p["lopre"] * np.log(grid)
                  + p["roa"] * roa_med + p["gear"] * gear_med)
    fig, ax = plt.subplots(figsize=(7, 4.6))
    over = fr["reach"] >= 1
    ax.scatter(fr.loc[~over, "opre"], fr.loc[~over, "pay"], s=10, alpha=0.4,
               color=BLUE, edgecolors="none", label="underpaid (below line)")
    ax.scatter(fr.loc[over, "opre"], fr.loc[over, "pay"], s=10, alpha=0.4,
               color=RED, edgecolors="none", label="overpaid (above line)")
    ax.plot(grid, line, color="black", lw=2.2, label="fair-pay line (peers)")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("company size — sales  (1000€)")
    ax.set_ylabel("board pay  (1000€)")
    ax.set_title(f"The peer benchmark: pay vs size  (slope β = {fit['beta']:.2f})")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    return _save(fig, "03_benchmark_fit")


# ---- 04 fit across firm size (residual diagnostic) ------------------------ #
def fig04(d):
    _style()
    fr = d["fit"]["frame"].copy(); fr["premium"] = np.exp(fr["eps"])
    fig, ax = plt.subplots(figsize=(7, 4.0))
    ax.scatter(fr["opre"], fr["premium"], s=10, alpha=0.3, color=BLUE, edgecolors="none")
    ax.axhline(1, color="black", lw=1.6, ls="--", label="on the benchmark")
    bins = pd.qcut(np.log(fr["opre"]), 12, duplicates="drop")
    med = fr.groupby(bins, observed=True).agg(x=("opre", "median"), y=("premium", "median"))
    ax.plot(med["x"], med["y"], "-o", color=RED, lw=2, ms=4, label="median by size band")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("company size — sales (1000€)")
    ax.set_ylabel("pay premium (1 = on benchmark)")
    ax.set_title("Does the benchmark fit evenly across sizes?  (flat red = yes)")
    ax.legend(frameon=False, fontsize=9)
    return _save(fig, "04_fit_by_size")


# ---- 05 pay-premium distribution ------------------------------------------ #
def fig05(d):
    _style()
    p = d["reach"]["premium"]; p = p[(p > 0) & np.isfinite(p)]
    lp = np.log10(p); p90, p10, p50 = p.quantile(0.9), p.quantile(0.1), p.median()
    fig, ax = plt.subplots(figsize=(7, 3.9))
    ax.hist(lp, bins=55, color=BLUE, alpha=0.85)
    ax.axvline(0, color="black", lw=1.6, ls="--", label="on benchmark (1×)")
    ax.axvline(np.log10(p90), color=RED, lw=1.6, label=f"top 10% ≥ +{(p90-1)*100:.0f}%")
    ticks = [0.25, 0.5, 1, 2, 4, 8]
    ax.set_xticks([np.log10(t) for t in ticks])
    ax.set_xticklabels([f"{t:g}×" for t in ticks])
    ax.set_xlabel("pay premium  (actual ÷ benchmark pay)")
    ax.set_ylabel("company-years")
    ax.set_title("How far pay sits above or below its benchmark")
    ax.legend(frameon=False, fontsize=9)
    return _save(fig, "05_premium_distribution")


# ---- 06 premium vs size, with 10-90 spread + names of extremes ------------ #
def fig06(d):
    _style()
    fr = d["fit"]["frame"].copy(); fr["premium"] = np.exp(fr["eps"])
    fr = fr[fr["premium"] > 0]
    name = d["fy"].drop_duplicates("isin").set_index("isin")["company_shortname"]
    fr["company"] = fr["isin"].map(name)
    bins = pd.qcut(np.log(fr["opre"]), 10, duplicates="drop")
    g = fr.groupby(bins, observed=True).agg(
        x=("opre", "median"), med=("premium", "median"),
        p10=("premium", lambda s: s.quantile(.10)),
        p90=("premium", lambda s: s.quantile(.90)))
    fig, ax = plt.subplots(figsize=(7.4, 4.4))
    ax.scatter(fr["opre"], fr["premium"], s=8, alpha=0.13, color=BLUE, edgecolors="none")
    ax.fill_between(g["x"], g["p10"], g["p90"], color=RED, alpha=0.15,
                    label="10th–90th percentile")
    ax.plot(g["x"], g["med"], "-o", color=RED, lw=2, ms=4, label="median")
    ax.axhline(1, color="black", lw=1.4, ls="--", label="on benchmark")
    # name the most extreme firms (premium > 4x), one label per firm
    lab = fr.sort_values("premium", ascending=False).drop_duplicates("isin").head(6)
    for _, r in lab.iterrows():
        ax.annotate(f"{r['company']} {int(r['year'])}", (r["opre"], r["premium"]),
                    fontsize=8.5, fontweight="bold",
                    xytext=(5, 2), textcoords="offset points", color="black")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("company size — sales (€)")
    ax.set_ylabel("pay premium (1 = on benchmark)")
    ax.set_title("Do small or big firms pay more above benchmark?")
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    return _save(fig, "06_premium_vs_size")


# ---- 07 bucket coverage --------------------------------------------------- #
def fig07(d):
    _style()
    cov = d["b3"]["coverage"]
    order = ["Fixed", "STI", "LTI"]
    vals = [cov[b]["share_used"] * 100 for b in order]
    fig, ax = plt.subplots(figsize=(5.6, 3.8))
    ax.bar(order, vals, color=[BUCKET_COL[b] for b in order], alpha=0.85)
    for i, v in enumerate(vals):
        ax.text(i, v + 1.5, f"{v:.0f}%", ha="center", fontsize=11)
    ax.set_ylim(0, 108); ax.set_ylabel("share of firms that use it (%)")
    ax.set_title("Which pay forms firms actually use")
    return _save(fig, "07_bucket_coverage")


# ---- 08 pay mix over time ------------------------------------------------- #
def fig08(d):
    _style()
    bv = part3_buckets.bucket_values(d["fy"], "3")
    tot = bv.groupby(["year", "bucket"])["value"].sum().unstack("bucket")
    share = tot.div(tot.sum(axis=1), axis=0) * 100
    order = ["Fixed", "STI", "LTI"]
    fig, ax = plt.subplots(figsize=(7, 3.8))
    bottom = np.zeros(len(share))
    for b in order:
        ax.bar(share.index, share[b], bottom=bottom, color=BUCKET_COL[b],
               alpha=0.85, label=b)
        bottom += share[b].values
    ax.set_ylabel("share of total pay (%)"); ax.set_xlabel("year")
    ax.set_ylim(0, 100)
    ax.set_title("What pay is made of, over time")
    ax.legend(frameon=False, ncol=3, fontsize=10, loc="lower center")
    return _save(fig, "08_pay_mix")


# ---- 09 where overpayment hides (gap framing) ----------------------------- #
def fig09(d):
    _style()
    h = d["hidden"].copy()
    h = h[(h["total_premium"] > 0) & (h["worst_form_premium"] > 0)]
    h["gap_pct"] = (np.exp(h["hidden_stretch"]) - 1) * 100   # top form vs the parts-average, %
    name = d["fy"].drop_duplicates("isin").set_index("isin")["company_shortname"]
    h["company"] = h["isin"].map(name)
    fig, ax = plt.subplots(figsize=(7.4, 4.5))
    for b, col in BUCKET_COL.items():
        s = h[h["worst_bucket"] == b]
        ax.scatter(s["total_premium"], s["gap_pct"], s=14, alpha=0.5,
                   color=col, edgecolors="none", label=f"piled into {b}")
    ax.axhline(0, color="black", lw=1.4, ls="--", label="evenly spread (0)")
    # name the biggest concentration in EACH form (so 'big bonus' etc. is visible)
    for b in ("Fixed", "STI", "LTI"):
        r = h[h["worst_bucket"] == b].nlargest(1, "gap_pct")
        if len(r):
            r = r.iloc[0]
            ax.annotate(f"{r['company']} {int(r['year'])} ({b})",
                        (r["total_premium"], r["gap_pct"]), fontsize=8.5,
                        fontweight="bold", xytext=(5, 0), textcoords="offset points")
    ax.set_xscale("log")
    ax.set_xlabel("headline pay premium (1 = on benchmark)")
    ax.set_ylabel("biggest pay form - total (%)")
    ax.set_title("Where pay is concentrated (one form piled above the rest)")
    ax.legend(frameon=False, fontsize=8.5, loc="upper right")
    return _save(fig, "09_where_hidden")


# ---- 09b explainer: why the gap can be below 0 ---------------------------- #
def fig09b(d):
    _style()
    h = d["hidden"]
    w = d["b3"]["reach_long"].pivot_table(index=["isin", "year"], columns="bucket",
                                          values="premium_b")
    tot = d["reach"].set_index(["isin", "year"])["premium"]
    name = d["fy"].drop_duplicates("isin").set_index("isin")["company_shortname"]
    h2 = h.copy(); h2["company"] = h2["isin"].map(name)
    conc = h2[(h2["company"] == "BMW") & (h2["year"] == 2017)]
    conc = conc.iloc[0] if len(conc) else h2[h2["worst_bucket"] == "STI"].nlargest(1, "hidden_stretch").iloc[0]
    bal = h2[h2["total_premium"].between(1.0, 2.0)].nsmallest(1, "hidden_stretch").iloc[0]
    fig, axes = plt.subplots(1, 2, figsize=(9, 4.3), sharey=True)
    forms = ["Fixed", "STI", "LTI"]
    for ax, row, tag in [(axes[0], bal, "BALANCED — gap ≈ 0"),
                         (axes[1], conc, "CONCENTRATED — gap high")]:
        i, y = row["isin"], int(row["year"])
        vals = [w.loc[(i, y)].get(b, np.nan) for b in forms]
        ax.bar(forms, vals, color=[BUCKET_COL[b] for b in forms], alpha=0.85)
        ax.axhline(row["total_premium"], color="black", ls="--", lw=1.8,
                   label=f"headline (parts) = {row['total_premium']:.2f}×")
        ax.axhline(1, color=GREY, ls=":", lw=1.3, label="on benchmark (1×)")
        for j, v in enumerate(vals):
            if pd.notna(v):
                ax.text(j, v * 1.06, f"{v:.2f}×", ha="center", fontsize=9.5)
        ax.set_yscale("log"); ax.set_ylim(0.05, 12)
        gp = (np.exp(row["hidden_stretch"]) - 1) * 100
        ax.set_title(f"{row['company']} {y}\n{tag}  (+{gp:.0f}%)", fontsize=11)
        ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    axes[0].set_ylabel("each pay form vs its OWN benchmark (×)")
    fig.suptitle("'Hidden stretch' = how far the top form sits above the firm's own average",
                 fontsize=12, fontweight="bold")
    return _save(fig, "09b_hidden_example")


# ---- 10 treadmill: nominal vs real ---------------------------------------- #
def fig10(d):
    _style()
    ta, tan = d["ta"], d["ta_nom"]
    nom = (np.exp(tan["delta_t"]) - 1) * 100      # log points -> % change vs 2006
    real = (np.exp(ta["delta_t"]) - 1) * 100
    fig, ax = plt.subplots(figsize=(7, 4.0))
    ax.plot(tan["year"], nom, "-o", color=ORANGE, lw=2.2, ms=4,
            label="nominal (pay as paid)")
    ax.plot(ta["year"], real, "-o", color=BLUE, lw=2.2, ms=4,
            label="real (inflation removed)")
    ax.axhline(0, color=GREY, lw=1, ls="--")
    ax.annotate(f"+{nom.iloc[-1]:.0f}%", (tan["year"].iloc[-1], nom.iloc[-1]),
                color=ORANGE, fontsize=11, fontweight="bold", xytext=(-4, 6),
                textcoords="offset points", ha="right")
    ax.annotate(f"+{real.iloc[-1]:.0f}%", (ta["year"].iloc[-1], real.iloc[-1]),
                color=BLUE, fontsize=11, fontweight="bold", xytext=(-4, -14),
                textcoords="offset points", ha="right")
    ax.set_xlabel("year"); ax.set_ylabel("pay drift vs 2006 (%)")
    ax.set_title("Is the pay bar creeping up?  (size & performance held fixed)")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    return _save(fig, "10_treadmill")


# ---- 11 secrecy: individual spread vs precise group means ----------------- #
def fig11(d):
    _style()
    r = d["reach"].merge(d["fy"][["isin", "year", "opting_out"]], on=["isin", "year"])
    r = r[(r["premium"] > 0) & r["opting_out"].notna()].copy()
    r["lp"] = np.log10(r["premium"])
    rng = np.random.default_rng(0)
    fig, ax = plt.subplots(figsize=(7.0, 4.4))
    for i, (grp, col) in enumerate([(0, BLUE), (1, RED)]):
        s = r.loc[r["opting_out"] == grp, "lp"]
        x = i + (rng.random(len(s)) - 0.5) * 0.28
        ax.scatter(x, s, s=8, alpha=0.16, color=col, edgecolors="none")
        m = s.mean(); ci = 1.96 * s.std() / np.sqrt(len(s))
        ax.errorbar(i, m, yerr=ci, fmt="o", color="black", ms=9, capsize=7, lw=2.4,
                    zorder=5, label="group mean ± 95% CI" if i == 0 else None)
    ax.axhline(0, color=GREY, lw=1, ls="--")
    ticks = [0.25, 0.5, 1, 2, 4]
    ax.set_yticks([np.log10(t) for t in ticks]); ax.set_yticklabels([f"{t:g}×" for t in ticks])
    ax.set_ylim(np.log10(0.12), np.log10(9))
    # opting out is not monolithic: extreme high AND extreme low premium both opt out
    ax.annotate("Ströer 2020: 62× ↑ (off top)", (1, np.log10(8.3)), ha="center",
                fontsize=8.5, color=RED, fontweight="bold")
    ax.annotate("Zalando 2017: 0.09× ↓ (off bottom)", (1, np.log10(0.14)), ha="center",
                fontsize=8.5, color=RED, fontweight="bold")
    ax.set_xticks([0, 1]); ax.set_xticklabels(["disclosed", "opted out\n(hid pay)"])
    ax.set_ylabel("pay premium")
    ax.set_xlabel("dots = individual firm-years (overlap a lot) · black = the average "
                  "(precisely different)", fontsize=9.5)
    ax.set_title("Firms that hide pay overpay more")
    ax.annotate(f"controlled ρ = +{d['secrecy']['rho']:.2f}  (p < 0.001)",
                (0.025, 0.045), xycoords="axes fraction", ha="left", va="bottom",
                fontsize=10, color=GREY)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    return _save(fig, "11_secrecy")


# ---- 12 CEO concentration ------------------------------------------------- #
def fig12(d):
    _style()
    by = d["conc"]["by_year"]
    med = by.groupby("year")["C"].median()
    fig, ax = plt.subplots(figsize=(7, 3.8))
    ax.plot(med.index, med.values, "-o", color=RED, lw=2, ms=4)
    z = np.polyfit(med.index, med.values, 1)
    ax.plot(med.index, np.polyval(z, med.index), color=GREY, lw=1.2, ls="--",
            label=f"trend +{z[0]:.3f}/yr")
    ax.set_xlabel("year"); ax.set_ylabel("CEO pay ÷ median other exec")
    ax.set_title("The CEO premium is rising")
    ax.legend(frameon=False, fontsize=10)
    return _save(fig, "12_ceo_concentration")


# ---- 13 asymmetric ratchet ------------------------------------------------ #
def fig13(d):
    _style()
    fy = d["fy"].rename(columns={"ROA": "roa"})[["isin", "year", "roa"]].copy()
    fy["pay"] = d["fy"]["total_comp_bt_real"]
    fy = fy.dropna(subset=["roa", "pay"]); fy = fy[fy["pay"] > 0].sort_values(["isin", "year"])
    fy["lpay"] = np.log(fy["pay"]); g = fy.groupby("isin")
    fy["d_lpay"] = g["lpay"].diff(); fy["d_roa"] = g["roa"].diff(); fy["step"] = g["year"].diff()
    s = fy[fy["step"] == 1].dropna(subset=["d_lpay", "d_roa"])
    s = s[s["d_roa"].abs() < s["d_roa"].abs().quantile(0.98)]
    s = s.copy()
    s["pct_pay"] = (np.exp(s["d_lpay"]) - 1) * 100  # convert log-change to % change

    rt = d["ratchet"]
    fig, ax = plt.subplots(figsize=(7, 4.0))
    ax.scatter(s["d_roa"], s["pct_pay"], s=10, alpha=0.3, color=BLUE, edgecolors="none")

    xs_up = np.linspace(0, s["d_roa"].max(), 50)
    xs_dn = np.linspace(s["d_roa"].min(), 0, 50)
    # transform the fitted log-slope lines into % space: %change = exp(beta*x) - 1
    ax.plot(xs_up, (np.exp(rt["beta_up"] * xs_up) - 1) * 100, color=RED, lw=2.2,
            label=f"good years (slope {rt['beta_up']:+.3f})")
    ax.plot(xs_dn, (np.exp(rt["beta_dn"] * xs_dn) - 1) * 100, color=ORANGE, lw=2.2,
            label=f"bad years (slope {rt['beta_dn']:+.3f})")

    ax.axhline(0, color=GREY, lw=0.8); ax.axvline(0, color=GREY, lw=0.8)

    # call out a real "raised pay in a bad year" firm-year (top-left quadrant)
    name = d["fy"].drop_duplicates("isin").set_index("isin")["company_shortname"]
    s2 = s.copy(); s2["company"] = s2["isin"].map(name)
    ex = s2[(s2["company"] == "Heidelberg Cement") & (s2["year"] == 2009)]
    if len(ex):
        ex = ex.iloc[0]
        ax.scatter([ex["d_roa"]], [ex["pct_pay"]], s=70, facecolors="none",
                   edgecolors="black", lw=1.8, zorder=6)
        ax.annotate(f"{ex['company']} 2009:\nprofit {ex['d_roa']:+.0f}, pay {ex['pct_pay']:+.0f}%",
                    (ex["d_roa"], ex["pct_pay"]), fontsize=8.5, xytext=(14, 8),
                    textcoords="offset points", arrowprops=dict(arrowstyle="->", lw=1))

    ax.set_xlabel("change in profitability, year-on-year  (ROA, in points)")
    ax.set_ylabel("change in pay, year-on-year  (%)")
    ax.set_title("Pay up on good years, sticky on bad? — No (slopes ≈ equal)")
    ax.set_ylim(-200,200)
    ax.legend(frameon=False, fontsize=9, loc="lower right")
    return _save(fig, "13_ratchet")

# ---- 14 grant spike: does a big equity grant inflate pay? ----------------- #
def fig14(d):
    _style()
    fy, reach = d["fy"], d["reach"]
    p = fy[["isin", "year"]].copy()
    p["lti_grant"] = (fy["total_equity_grants_bt_real"].fillna(0)
                      + fy["multi_year_bonus_grants_bt_real"].fillna(0))
    p["total_pay"] = fy["total_comp_bt_real"]
    p = p.merge(reach[["isin", "year", "premium"]], on=["isin", "year"], how="inner")
    p = p.dropna(subset=["total_pay", "premium"]); p = p[p["total_pay"] > 0]
    p["grant_share"] = p["lti_grant"] / p["total_pay"]

    # event study around a big-grant year (grant > 2x firm median, >25% of pay)
    fmed = p.groupby("isin")["lti_grant"].transform("median")
    p["spike"] = (p["lti_grant"] > 2 * fmed) & (p["grant_share"] > 0.25) & (p["lti_grant"] > 0)
    prem = p.set_index(["isin", "year"])["premium"]
    rows = []
    for _, s in p[p["spike"]].iterrows():
        for k in range(-2, 3):
            v = prem.get((s["isin"], s["year"] + k), np.nan)
            if pd.notna(v):
                rows.append({"k": k, "premium": v})
    ev = pd.DataFrame(rows).groupby("k")["premium"].agg(["median", "mean"])
    nsp = int(p["spike"].sum()); nfi = p[p["spike"]]["isin"].nunique()

    fig, ax = plt.subplots(figsize=(7.6, 4.6))
    ax.plot(ev.index, ev["mean"], "-o", color=RED, lw=2.4, ms=6,
            label="mean premium  (plain average across the firms)")
    ax.plot(ev.index, ev["median"], "-o", color=BLUE, lw=2, ms=5,
            label="median premium  (the middle firm)")
    ax.axhline(1, color=GREY, ls="--", lw=1.2, label="on benchmark (1×)")
    ax.axvline(0, color=GREY, ls=":", lw=1)
    ax.annotate(f"mean → {ev['mean'][0]:.1f}×", (0, ev["mean"][0]), color=RED,
                fontsize=11, fontweight="bold", xytext=(10, -10), textcoords="offset points")
    ax.set_xticks([-2, -1, 0, 1, 2])
    ax.set_xlabel("years relative to the big equity / LTI grant  (year 0)")
    ax.set_ylabel("pay premium  (pay ÷ its benchmark)")
    ax.set_title(f"A big equity grant spikes pay — then it reverts\n"
                 f"({nsp} big-grant years, {nfi} firms · grant = equity + multi-year bonus)",
                 fontsize=11)
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    return _save(fig, "14_grant_spike")


# ---- ranking table -> markdown -------------------------------------------- #
def inject_table(d, top=15):
    import re
    rk = d["ranking"].head(top).copy()
    prem_by_firm = d["reach"].groupby("isin")["premium"].median()
    rk["med_premium"] = rk["isin"].map(prem_by_firm)
    hdr = "| Rank | Company | Premium | Hidden | Secrecy | CEO ratio | Score |"
    sep = "|---:|:---|---:|---:|---:|---:|---:|"
    rows = [hdr, sep]
    for _, r in rk.iterrows():
        ceo = "–" if pd.isna(r["median_C"]) else f"{r['median_C']:.1f}"
        hid = "–" if pd.isna(r["median_hidden"]) else f"+{(np.exp(r['median_hidden'])-1)*100:.0f}%"
        rows.append(f"| {int(r['rank'])} | {r['company']} | {r['med_premium']:.1f}× | "
                    f"{hid} | {r['secrecy_share']*100:.0f}% | {ceo} | {r['score']:.2f} |")
    block = "<!-- TABLE:start -->\n" + "\n".join(rows) + "\n<!-- TABLE:end -->"
    md = cfg.PROJECT_ROOT / "PRESENTATION.md"
    txt = md.read_text(encoding="utf-8")
    if "<!-- TABLE:start -->" in txt:               # idempotent refresh
        txt = re.sub(r"<!-- TABLE:start -->.*?<!-- TABLE:end -->", block, txt, flags=re.S)
    else:                                            # first injection
        txt = txt.replace("<!-- TABLE:redflag_ranking -->", block)
    md.write_text(txt, encoding="utf-8")


def main():
    cfg.enable_utf8_stdout()
    d = _data()
    figs = [fig01, fig02, fig03, fig04, fig05, fig06, fig07,
            fig08, fig09, fig09b, fig10, fig11, fig12, fig13, fig14]
    for f in figs:
        print("  ", f(d).name)
    inject_table(d)
    print("ranking table injected into PRESENTATION.md")


if __name__ == "__main__":
    main()