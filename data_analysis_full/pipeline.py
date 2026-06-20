"""End-to-end orchestrator for Parts 0-4. Run with:  python -m src.pipeline

Builds the cleaned tables, fits the benchmark, computes reach, splits reach by
bucket (3-bucket headline + 6-bucket detail), and measures the treadmill. Writes
intermediates/outputs to build/ and prints a sanity summary.
"""
from __future__ import annotations
import sys, io
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import numpy as np
import pandas as pd

from . import config as C
from . import loaders, part0_clean, part1_benchmark, part2_reach
from . import part3_buckets, part4_treadmill, part6_redflags, plots


def reconcile_person_to_board(person_year, firm_year) -> dict:
    """Validation: the sum of *raw reported* person total_comp must equal the
    board total_comp (a data-integrity check; uses raw, not annualized/deflated,
    numbers - annualization deliberately scales partial-year execs up)."""
    psum = (person_year.groupby(["isin", "year"])["total_comp"].sum()
            .rename("person_sum"))
    b = firm_year.set_index(["isin", "year"])["total_comp_bt"]
    m = pd.concat([b, psum], axis=1).dropna()
    m = m[m["total_comp_bt"] > 0]
    ratio = m["person_sum"] / m["total_comp_bt"]
    return {"matched": int(len(m)),
            "median_ratio": float(ratio.median()),
            "within_5pct": int(ratio.between(0.95, 1.05).sum())}


def run(verbose: bool = True) -> dict:
    # --- Part 0 ---------------------------------------------------------
    firm_year = part0_clean.build_firm_year()
    person_year = part0_clean.build_person_year()
    rec = reconcile_person_to_board(person_year, firm_year)

    # --- Part 1 + 2 -----------------------------------------------------
    fit = part1_benchmark.fit_benchmark(firm_year)
    reach = part2_reach.reach_from_benchmark(fit)

    # --- Part 3 ---------------------------------------------------------
    b3 = part3_buckets.fit_bucket_reach(firm_year, scheme="3")
    b6 = part3_buckets.fit_bucket_reach(firm_year, scheme="6")
    # direction-aware deliverable: where is overpayment hidden?
    hidden3 = part3_buckets.hidden_stretch(b3["reach_long"], reach)
    div3 = part3_buckets.divergence(b3["reach_long"])   # plan's spread (winsorized)

    # --- Part 4 ---------------------------------------------------------
    ta = part4_treadmill.route_a(fit)
    tb = part4_treadmill.route_b(firm_year)

    # --- Part 6 ---------------------------------------------------------
    ratchet = part6_redflags.asymmetric_ratchet(firm_year)
    secrecy = part6_redflags.secrecy_premium(reach, firm_year)
    concentration = part6_redflags.internal_concentration(person_year)
    ranking = part6_redflags.redflag_ranking(
        firm_year, reach, hidden3, concentration["by_year"])

    # --- persist --------------------------------------------------------
    firm_year.to_csv(C.BUILD_DIR / "firm_year.csv", index=False, encoding="utf-8")
    person_year.to_csv(C.BUILD_DIR / "person_year.csv", index=False, encoding="utf-8")
    reach.to_csv(C.BUILD_DIR / "reach.csv", index=False, encoding="utf-8")
    b3["reach_long"].to_csv(C.BUILD_DIR / "bucket_reach_3.csv", index=False, encoding="utf-8")
    b6["reach_long"].to_csv(C.BUILD_DIR / "bucket_reach_6.csv", index=False, encoding="utf-8")
    hidden3.to_csv(C.BUILD_DIR / "hidden_stretch_3.csv", index=False, encoding="utf-8")
    div3.to_csv(C.BUILD_DIR / "divergence_3.csv", index=False, encoding="utf-8")
    ta.to_csv(C.BUILD_DIR / "treadmill_year_effects.csv", index=False, encoding="utf-8")
    ranking.to_csv(C.BUILD_DIR / "redflag_ranking.csv", index=False, encoding="utf-8")
    part6_redflags.redflag_to_latex(ranking, C.BUILD_DIR / "redflag_table.tex", top=15)

    # figures (PDF for LaTeX + PNG)
    out = {"reconcile": rec, "fit": fit, "reach": reach,
           "buckets_3": b3, "buckets_6": b6, "div3": div3, "hidden3": hidden3,
           "treadmill_a": ta, "treadmill_b": tb,
           "ratchet": ratchet, "secrecy": secrecy, "concentration": concentration,
           "ranking": ranking, "firm_year": firm_year, "person_year": person_year}
    figs = plots.make_all(out)
    out["figures"] = figs

    if verbose:
        _print_summary(out)
    return out


def _print_summary(o: dict) -> None:
    rec, fit = o["reconcile"], o["fit"]
    print("=" * 70)
    print("EXECUTIVE-PAY GAP PIPELINE - SUMMARY")
    print("=" * 70)
    print(f"[Part 0] firm-years: {len(o['firm_year'])} | "
          f"person-years: {len(o['person_year'])}")
    print(f"[Part 0] person->board reconciliation: {rec['within_5pct']}/"
          f"{rec['matched']} within 5% (median ratio {rec['median_ratio']:.3f})")
    print(f"[Part 1] benchmark median regression: n={fit['n']}  "
          f"beta(log opre)={fit['beta']:.3f}  (plan expects ~0.30)")
    r = o["reach"]["reach"]
    print(f"[Part 2] reach: median={r.median():.3f}  p90={r.quantile(.9):.2f}  "
          f"max={r.max():.1f}")
    print("[Part 3] 3-bucket coverage (extensive margin) & intensive beta_b:")
    for b, cov in o["buckets_3"]["coverage"].items():
        print(f"          {b:6s}: used {cov['share_used']*100:5.1f}%  "
              f"(n_used={cov['n_used']:4d})  beta_b={o['buckets_3']['betas'][b]:+.3f}")
    hid = o["hidden3"]
    where = hid.head(40)["worst_bucket"].value_counts().to_dict()
    print(f"[Part 3] hidden stretch (overpayment concealed in one form): "
          f"{len(hid)} firm-years; where it hides (top 40) -> {where}")
    h0 = hid.iloc[0]
    print(f"          worst case: {h0['worst_bucket']} premium {h0['worst_form_premium']:.0f}x "
          f"vs headline premium {h0['total_premium']:.1f}x")
    tb = o["treadmill_b"]
    w1 = tb["weighting_1"]
    print(f"[Part 4] treadmill {tb['year0']}->{tb['yearT']}: total dlog pay="
          f"{tb['total_change']:+.3f}; treadmill share={w1['treadmill_share']*100:.0f}% "
          f"(weighting 1)")
    print(f"[Part 4] year effects delta_t span: "
          f"{o['treadmill_a']['delta_t'].min():+.3f} .. {o['treadmill_a']['delta_t'].max():+.3f}")
    rt, sc, cc = o["ratchet"], o["secrecy"], o["concentration"]
    print(f"[Part 6] asymmetric ratchet: beta_up={rt['beta_up']:+.3f} "
          f"beta_dn={rt['beta_dn']:+.3f}  flag={rt['flag']}")
    print(f"[Part 6] secrecy premium (opting_out): rho={sc['rho']:+.3f} "
          f"p={sc['p']:.3f}  flag={sc['flag']}")
    print(f"[Part 6] CEO concentration: median C={cc['median_C']:.2f}  "
          f"{cc['C_first_year']:.2f}->{cc['C_last_year']:.2f}  "
          f"slope/yr={cc['slope_per_year']:+.4f}  flag={cc['flag']}")
    rk = o["ranking"]
    print(f"[Part 6] red-flag ranking: {len(rk)} firms scored; top 3 -> "
          + ", ".join(f"{r.company}({r.score:.2f})"
                      for r in rk.head(3).itertuples()))
    print("=" * 70)
    print(f"outputs written to {C.BUILD_DIR}")
    if "figures" in o:
        print("figures: " + ", ".join(p.name for p in o["figures"].values()))


if __name__ == "__main__":
    run()
