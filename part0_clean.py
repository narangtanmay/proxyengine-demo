"""Part 0 - clean the raw data into the firm-year (X^F) and person-year (X^P)
tables that feed the rest of the pipeline.

Steps (plan Part 0, amended by the data review):
  * parse fiscal-year dates; L = fy_end - fy_begin (days).
  * annualize PERSON pay by L/days (person was in post `days` of an L-day year).
    The board total is left raw - we feed Part 1 the raw total_comp_bt so firm
    totals are not inflated (person pay already reconciles to the board total).
  * deflate every money column to real euros with the CPI (base CPI_BASE_YEAR).
  * join the deduplicated ORBIS fundamentals on (isin, year).
"""
from __future__ import annotations
import numpy as np
import pandas as pd

from . import config as C
from . import loaders


def _parse_dt(s: pd.Series) -> pd.Series:
    # dates look like "01jan2017"; quotes already stripped by loaders for isin
    return pd.to_datetime(s.str.strip().str.strip('"'), format="%d%b%Y",
                          errors="coerce")


def _deflator(year: pd.Series, cpi: dict[int, float]) -> pd.Series:
    base = cpi[C.CPI_BASE_YEAR]
    return year.map(lambda y: (cpi.get(int(y)) / base)
                    if pd.notna(y) and int(y) in cpi else np.nan)


# board money columns to deflate
_BOARD_MONEY = ["salary_bt", "one_year_bonus_bt", "multi_year_bonus_bt",
                "multi_year_bonus_grants_bt", "multi_year_bonus_payout_bt",
                "total_equity_grants_bt", "stock_grants_bt", "option_grants_bt",
                "other_annual_bt", "total_comp_bt", "one_time_payment_bt",
                "pension_bt", "total_comp_pens_and_one_time_bt"]
_PERSON_MONEY = ["salary", "one_year_bonus", "multi_year_bonus",
                 "multi_year_bonus_grants", "multi_year_bonus_payout",
                 "total_equity_grants", "stock_grants", "option_grants",
                 "other_annual_comp", "total_comp", "pension",
                 "one_time_payment", "total_comp_pens_and_one_time"]


def build_firm_year(board=None, orbis=None, cpi=None) -> pd.DataFrame:
    """X^F: one row per (isin, year) with real board pay + ORBIS fundamentals."""
    board = loaders.load_board() if board is None else board.copy()
    orbis = loaders.build_orbis_firm_year() if orbis is None else orbis.copy()
    cpi = C.load_cpi() if cpi is None else cpi

    board["fy_begin_dt"] = _parse_dt(board["fy_begin"])
    board["fy_end_dt"] = _parse_dt(board["fy_end"])
    board["L_days"] = (board["fy_end_dt"] - board["fy_begin_dt"]).dt.days + 1

    defl = _deflator(board["year"], cpi)
    for c in _BOARD_MONEY:
        board[c + "_real"] = board[c] / defl

    orbis = orbis[["isin", "year", "OPRE", "ROA", "GEAR", "TOAS", "ROE",
                   "SOLR", "CONSCODE"]].copy()
    orbis["year"] = pd.to_numeric(orbis["year"], errors="coerce").astype("Int64")
    fy = board.merge(orbis, on=["isin", "year"], how="left")
    return fy


def build_person_year(person=None, board=None, cpi=None) -> pd.DataFrame:
    """X^P: one row per (exec_id, isin, year) with annualized, real pay."""
    person = loaders.load_person() if person is None else person.copy()
    board = loaders.load_board() if board is None else board.copy()
    cpi = C.load_cpi() if cpi is None else cpi

    # bring fiscal-year length L from the board file
    board["fy_begin_dt"] = _parse_dt(board["fy_begin"])
    board["fy_end_dt"] = _parse_dt(board["fy_end"])
    board["L_days"] = (board["fy_end_dt"] - board["fy_begin_dt"]).dt.days + 1
    L = board[["isin", "year", "L_days"]]

    p = person.merge(L, on=["isin", "year"], how="left")
    # annualize: scale partial-year pay up to a full L-day year
    days = p["days"].where(p["days"] > 0)
    scale = (p["L_days"] / days).clip(upper=4.0)   # cap runaway scaling
    scale = scale.fillna(1.0)
    defl = _deflator(p["year"], cpi)
    for c in _PERSON_MONEY:
        p[c + "_ann"] = p[c] * scale
        p[c + "_real"] = p[c + "_ann"] / defl
    p["ann_scale"] = scale
    return p


if __name__ == "__main__":
    # Build & inspect the cleaned tables:  python -m src.part0_clean
    C.enable_utf8_stdout()
    fy = build_firm_year()
    py = build_person_year()
    print("X^F firm_year   :", fy.shape, "| has ORBIS OPRE in %d rows"
          % int(fy["OPRE"].notna().sum()))
    print("X^P person_year :", py.shape)

    # show annualization on a partial-year executive (days < fiscal year length)
    part = py[(py["days"] > 0) & (py["days"] < 250) & (py["total_comp"] > 0)].iloc[0]
    print(f"\nAnnualization example: {part['exec_fullname']} @ {part['company_shortname']}"
          f" {int(part['year'])}")
    print(f"   in post {int(part['days'])} of {int(part['L_days'])} days  ->  scale "
          f"x{part['ann_scale']:.2f}")
    print(f"   total_comp raw {part['total_comp']:.0f}  -> annualized "
          f"{part['total_comp_ann']:.0f}  -> real(2015) {part['total_comp_real']:.0f}")

    # reconciliation: raw person sum vs board total
    psum = py.groupby(["isin", "year"])["total_comp"].sum()
    b = fy.set_index(["isin", "year"])["total_comp_bt"]
    import pandas as _pd
    m = _pd.concat([b, psum.rename("ps")], axis=1).dropna()
    m = m[m["total_comp_bt"] > 0]
    r = m["ps"] / m["total_comp_bt"]
    print(f"\nReconciliation: {(r.between(0.95,1.05)).sum()}/{len(m)} firm-years "
          f"within 5%% (median ratio {r.median():.3f})")
