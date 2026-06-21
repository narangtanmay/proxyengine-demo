"""Part 2 - turn the residual into two reader-friendly numbers.

    pay premium   = exp( eps )       <- PRIMARY, intuitive % above/below benchmark
    size-equiv.   = exp( eps / beta) <- SECONDARY ("you pay like a firm X your size")

`premium` is the honest headline: premium = 1.2 means 20% above the benchmark,
2.0 means double. `reach` divides by the small slope beta (~0.4), which amplifies
the same gap into a vivid but easy-to-overstate "size-equivalent" number - kept
only as a secondary visual. Both are monotonic in eps, so any ranking is identical.
"""
from __future__ import annotations
import numpy as np
import pandas as pd


def add_reach(frame: pd.DataFrame, beta: float, eps_col: str = "eps",
              out_col: str = "reach") -> pd.DataFrame:
    df = frame.copy()
    df["premium"] = np.exp(df[eps_col])          # primary: % above/below benchmark
    df[out_col] = np.exp(df[eps_col] / beta)     # secondary: size-equivalent
    return df


def reach_from_benchmark(fit: dict) -> pd.DataFrame:
    """Convenience: take Part-1 output dict, return frame with a reach column."""
    return add_reach(fit["frame"], fit["beta"])


if __name__ == "__main__":
    # Compute & inspect reach:  python -m src.part2_reach
    from . import config as _cfg, part0_clean, part1_benchmark
    _cfg.enable_utf8_stdout()
    fit = part1_benchmark.fit_benchmark(part0_clean.build_firm_year())
    r = reach_from_benchmark(fit)
    print(f"reach = exp(eps / beta),  beta = {fit['beta']:.3f}")
    print("\ndistribution:")
    print(r["reach"].describe(percentiles=[.5, .9, .95, .99]).round(2).to_string())
    print("\nmedian ~ 1.0 by construction (median regression). Most overpaid:")
    print(r.nlargest(5, "reach")[["isin", "year", "opre", "pay", "reach"]]
          .to_string(index=False))
