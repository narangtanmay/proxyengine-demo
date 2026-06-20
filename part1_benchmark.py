"""Part 1 - the benchmark curve (median regression of log pay on size).

    Q_0.5( log total_comp ) = a + b log(opre) + g1 roa + g2 gear + delta_t

Fit at the median (quantile 0.5) so a few giant packages do not drag the
benchmark up. Returns the fitted model, the slope beta (expected ~0.3), the
year effects delta_t (used by Part 4), and the estimation frame with the
residual eps appended (the raw material for reach).
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf


def estimation_frame(firm_year: pd.DataFrame,
                     pay_col: str = "total_comp_bt_real",
                     size_col: str = "OPRE") -> pd.DataFrame:
    """Rows usable for the regression: positive pay & size, performance and
    leverage present."""
    df = firm_year.copy()
    df = df.rename(columns={size_col: "opre", "ROA": "roa", "GEAR": "gear"})
    df = df[["isin", "year", "opre", "roa", "gear"]].assign(pay=firm_year[pay_col])
    df = df.dropna(subset=["pay", "opre", "roa", "gear"])
    df = df[(df["pay"] > 0) & (df["opre"] > 0)].copy()
    df["ltc"] = np.log(df["pay"])
    df["lopre"] = np.log(df["opre"])
    df["year"] = df["year"].astype(int)
    return df.reset_index(drop=True)


def fit_benchmark(firm_year: pd.DataFrame, q: float = 0.5,
                  pay_col: str = "total_comp_bt_real") -> dict:
    df = estimation_frame(firm_year, pay_col=pay_col)
    model = smf.quantreg("ltc ~ lopre + roa + gear + C(year)", df).fit(q=q)

    df = df.copy()
    df["fitted"] = model.fittedvalues
    df["eps"] = df["ltc"] - df["fitted"]

    beta = float(model.params["lopre"])

    # delta_t: year effects relative to the base year, plus intercept
    base_year = df["year"].min()
    year_eff = {int(base_year): 0.0}
    for name, val in model.params.items():
        if name.startswith("C(year)[T."):
            yr = int(name.split("C(year)[T.")[1].rstrip("]"))
            year_eff[yr] = float(val)

    return {
        "model": model, "beta": beta, "frame": df,
        "year_effects": dict(sorted(year_eff.items())),
        "n": len(df), "pseudo_r2": float(getattr(model, "prsquared", np.nan)),
    }


if __name__ == "__main__":
    # Fit & inspect the benchmark curve:  python -m src.part1_benchmark
    from . import config as _cfg, part0_clean
    _cfg.enable_utf8_stdout()
    fy = part0_clean.build_firm_year()
    fit = fit_benchmark(fy)
    print("Median regression  log(total_comp) ~ log(opre) + roa + gear + year FE")
    print(f"   n = {fit['n']}  firm-years")
    print(f"   beta(log opre) = {fit['beta']:.3f}   (plan target ~0.30)")
    print(f"   pseudo R^2     = {fit['pseudo_r2']:.3f}")
    print("\n   year effects delta_t (first/last 3):")
    ye = list(fit["year_effects"].items())
    for y, v in ye[:3] + [("...", None)] + ye[-3:]:
        print(f"      {y}: {'' if v is None else f'{v:+.3f}'}")
    print("\n   residual eps -> reach raw material; sample rows:")
    print(fit["frame"][["isin", "year", "pay", "opre", "eps"]].head(4)
          .to_string(index=False))
