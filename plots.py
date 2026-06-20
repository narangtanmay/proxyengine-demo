"""Figures for the report (Parts 2-4). Saved as vector PDF (for LaTeX) + PNG.

Three plots:
  * treadmill      - the year effects delta_t path (Part 4 Route A).
  * reach_dist     - distribution of reach on a log axis (Part 2), with the
                     median (=1, fair) and top-decile flag threshold marked.
  * bucket_divergence - reach^(b) per headline bucket on a log axis (Part 3);
                     the vertical spread between buckets *is* the divergence.
"""
from __future__ import annotations
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from . import config as cfg

FIG_DIR = cfg.BUILD_DIR / "figures"
FIG_DIR.mkdir(exist_ok=True)

_BLUE, _RED, _GREY = "#2b6cb0", "#aa1e1e", "#555555"


def _style():
    plt.rcParams.update({
        "figure.dpi": 110, "savefig.dpi": 200, "font.size": 11,
        "axes.titlesize": 10.5, "axes.spines.top": False,
        "axes.spines.right": False, "axes.grid": True, "grid.alpha": 0.25,
        "axes.axisbelow": True, "figure.autolayout": True,
    })


def _save(fig, name: str) -> Path:
    pdf = FIG_DIR / f"{name}.pdf"
    fig.savefig(pdf)
    fig.savefig(FIG_DIR / f"{name}.png")
    plt.close(fig)
    return pdf


def fig_treadmill(year_effects: dict) -> Path:
    _style()
    yrs = sorted(year_effects)
    vals = [year_effects[y] for y in yrs]
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.plot(yrs, vals, "-o", color=_BLUE, lw=2, ms=4)
    ax.axhline(0, color=_GREY, lw=0.8, ls="--")
    ax.set_xlabel("year"); ax.set_ylabel(r"year effect $\delta_t$ (log pts)")
    ax.set_title(r"Part 4 - treadmill: benchmark pay drift $\delta_t$")
    return _save(fig, "treadmill")


def fig_reach_distribution(reach: pd.Series) -> Path:
    _style()
    r = reach[(reach > 0) & np.isfinite(reach)]
    lr = np.log10(r)
    p90 = r.quantile(0.90)
    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.hist(lr, bins=60, color=_BLUE, alpha=0.8)
    ax.axvline(0, color=_GREY, lw=1.2, ls="--", label="reach = 1 (fair)")
    ax.axvline(np.log10(p90), color=_RED, lw=1.4, ls="-",
               label=f"top decile = {p90:.1f}")
    ax.set_xlabel(r"$\log_{10}$ reach"); ax.set_ylabel("firm-years")
    ax.set_title("Part 2 - reach distribution (median = 1, long right tail)")
    ax.legend(frameon=False, fontsize=9)
    return _save(fig, "reach_distribution")


_BUCKET_COL = {"Fixed": "#2b6cb0", "STI": "#d97706", "LTI": "#aa1e1e"}


def fig_hidden_stretch(hidden_tbl: pd.DataFrame) -> Path:
    """Where overpayment hides: the most-overpaid pay bucket (y) vs the firm's
    headline total reach (x), per firm-year, log-log. The diagonal is 'no
    concealment'; points far ABOVE it pay ordinarily overall but stretch one
    pay form well beyond its norm. Colour = which form."""
    _style()
    d = hidden_tbl.copy()
    d = d[(d["total_premium"] > 0) & (d["worst_form_premium"] > 0)]
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    for b, col in _BUCKET_COL.items():
        s = d[d["worst_bucket"] == b]
        ax.scatter(s["total_premium"], s["worst_form_premium"], s=14, alpha=0.55,
                   color=col, label=f"hides in {b}", edgecolors="none")
    lim = [min(d["total_premium"].min(), d["worst_form_premium"].min()) * 0.8,
           d["worst_form_premium"].max() * 1.3]
    ax.plot(lim, lim, color=_GREY, lw=1.0, ls="--", label="no concealment (y=x)")
    ax.set_xscale("log"); ax.set_yscale("log")
    ax.set_xlabel("headline pay premium (Part 2)")
    ax.set_ylabel(r"most-stretched form premium  $\max_b\,\mathrm{premium}^{(b)}$")
    ax.set_title("Part 3 - where overpayment hides (above the line = concealed)")
    ax.legend(frameon=False, fontsize=8.5, loc="upper left")
    return _save(fig, "hidden_stretch")


def make_all(out: dict) -> dict:
    """Build every figure from a pipeline `run()` output dict."""
    return {
        "treadmill": fig_treadmill(out["fit"]["year_effects"]),
        "reach_distribution": fig_reach_distribution(out["reach"]["reach"]),
        "hidden_stretch": fig_hidden_stretch(out["hidden3"]),
    }


if __name__ == "__main__":
    # Generate the figures:  python -m src.plots
    from . import part0_clean, part1_benchmark, part2_reach, part3_buckets
    cfg.enable_utf8_stdout()
    fy = part0_clean.build_firm_year()
    fit = part1_benchmark.fit_benchmark(fy)
    reach = part2_reach.reach_from_benchmark(fit)
    reach_long = part3_buckets.fit_bucket_reach(fy, "3")["reach_long"]
    hidden3 = part3_buckets.hidden_stretch(reach_long, reach)
    figs = make_all({"fit": fit, "reach": reach, "hidden3": hidden3})
    for name, path in figs.items():
        print(f"   {name:20s} -> {path}")
