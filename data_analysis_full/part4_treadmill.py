"""Part 4 - the benchmark drifting upward (the treadmill).

Route A (free): the year effects delta_t from Part 1; a rising line is the
treadmill.

Route B (the quotable number): split the change in average log pay between the
first and last year into a "fundamentals" part (firms genuinely bigger/better)
and a "drift / treadmill" part (the curve itself shifting up):

    d log pay = b0'(Z_T - Z0)  +  Z_T'(b_T - b0)
                 fundamentals       drift / treadmill

with Z = (log opre, roa, gear), b fitted by OLS within each year.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf

from .part1_benchmark import estimation_frame


def route_a(fit: dict) -> pd.DataFrame:
    """Year effects as a tidy frame (year, delta_t)."""
    ye = fit["year_effects"]
    return pd.DataFrame({"year": list(ye.keys()), "delta_t": list(ye.values())})


def _year_ols(df: pd.DataFrame):
    m = smf.ols("ltc ~ lopre + roa + gear", df).fit()
    b = np.array([m.params["lopre"], m.params["roa"], m.params["gear"]])
    zbar = df[["lopre", "roa", "gear"]].mean().to_numpy()
    return b, zbar, float(m.params["Intercept"])


def route_b(firm_year: pd.DataFrame, pay_col: str = "total_comp_bt_real",
            year0: int | None = None, yearT: int | None = None,
            window: int = 3) -> dict:
    """Oaxaca-style split of the change in mean log pay. Reports both base-year
    weightings (the plan's known base-year ambiguity).

    To avoid dividing by a noisy single-year change, the two endpoints are
    `window`-year averages (first/last `window` years), not single years.
    """
    df = estimation_frame(firm_year, pay_col=pay_col)
    y_min, y_max = int(df["year"].min()), int(df["year"].max())
    year0 = y_min if year0 is None else year0
    yearT = y_max if yearT is None else yearT
    d0 = df[df["year"].between(year0, year0 + window - 1)]
    dT = df[df["year"].between(yearT - window + 1, yearT)]

    b0, z0, a0 = _year_ols(d0)
    bT, zT, aT = _year_ols(dT)

    total = (dT["ltc"].mean() - d0["ltc"].mean())

    # weighting 1: fundamentals at base coeffs, drift at end means
    fund_1 = float(b0 @ (zT - z0))
    drift_1 = float(zT @ (bT - b0)) + (aT - a0)
    # weighting 2 (swap reference): fundamentals at end coeffs, drift at base means
    fund_2 = float(bT @ (zT - z0))
    drift_2 = float(z0 @ (bT - b0)) + (aT - a0)

    return {
        "year0": year0, "yearT": yearT, "total_change": float(total),
        "weighting_1": {"fundamentals": fund_1, "drift": drift_1,
                        "treadmill_share": drift_1 / total if total else np.nan},
        "weighting_2": {"fundamentals": fund_2, "drift": drift_2,
                        "treadmill_share": drift_2 / total if total else np.nan},
    }


if __name__ == "__main__":
    # Inspect the treadmill:  python -m src.part4_treadmill
    from . import config as _cfg, part0_clean, part1_benchmark
    _cfg.enable_utf8_stdout()
    fy = part0_clean.build_firm_year()
    fit = part1_benchmark.fit_benchmark(fy)
    ta = route_a(fit)
    print("Route A - year effects delta_t (the treadmill, real euros):")
    print(ta.to_string(index=False))
    tb = route_b(fy)
    print(f"\nRoute B - decomposition {tb['year0']} -> {tb['yearT']}:")
    print(f"   total change in mean log pay = {tb['total_change']:+.3f}")
    for w in ("weighting_1", "weighting_2"):
        d = tb[w]
        print(f"   {w}: fundamentals={d['fundamentals']:+.3f}  drift={d['drift']:+.3f}"
              f"  treadmill share={d['treadmill_share']*100:.0f}%")
