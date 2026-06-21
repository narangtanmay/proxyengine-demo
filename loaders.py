"""Loaders for the three pay files and the ORBIS fundamentals dump.

The pay CSVs are pipe-delimited / latin-1. ORBIS is comma-delimited / latin-1
and is 858 MB, so it is streamed once, filtered to the pay-panel ISINs,
deduplicated to one row per (isin, year), and cached.
"""
from __future__ import annotations
import csv
import numpy as np
import pandas as pd

from . import config as C

# Money/numeric columns in the board file (everything ending _bt + counts)
_BOARD_NUM = [
    "salary_bt", "one_year_bonus_bt", "multi_year_bonus_bt",
    "multi_year_bonus_grants_bt", "multi_year_bonus_payout_bt",
    "total_equity_grants_bt", "stock_grants_bt", "option_grants_bt",
    "other_annual_bt", "total_comp_bt", "one_time_payment_bt", "pension_bt",
    "total_comp_pens_and_one_time_bt", "n_executives", "days_bt", "opting_out",
]
_PERSON_NUM = [
    "salary", "one_year_bonus", "multi_year_bonus", "multi_year_bonus_grants",
    "multi_year_bonus_payout", "total_equity_grants", "stock_grants",
    "option_grants", "other_annual_comp", "total_comp", "pension",
    "pension_missing", "one_time_payment", "total_comp_pens_and_one_time",
    "days", "ceo_flag_eoy", "cfo_flag_eoy",
]


def _read_pay(path) -> pd.DataFrame:
    return pd.read_csv(path, sep=C.PAY_SEP, encoding=C.PAY_ENCODING,
                       quotechar='"', dtype=str, keep_default_na=False)


def _to_num(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    for c in cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c].replace("", np.nan), errors="coerce")
    return df


def load_board() -> pd.DataFrame:
    """[BOARD] firm-year pay. Keys: isin, year."""
    df = _read_pay(C.BOARD_CSV)
    df["isin"] = df["isin"].str.strip()
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    return _to_num(df, _BOARD_NUM)


def load_person() -> pd.DataFrame:
    """[PERSON] exec-year pay. Keys: company_person_id, exec_id, isin, year."""
    df = _read_pay(C.PERSON_CSV)
    df["isin"] = df["isin"].str.strip()
    df["year"] = pd.to_numeric(df["year"], errors="coerce").astype("Int64")
    return _to_num(df, _PERSON_NUM)


def load_person_attrs() -> pd.DataFrame:
    """Person attributes / exec_id crosswalk (female, nationality, dob, ...)."""
    df = _read_pay(C.PERSON_ATTR_CSV)
    df["isin"] = df["isin"].str.strip()
    return df


def pay_isins() -> set[str]:
    b = load_board()["isin"]
    p = load_person()["isin"]
    return set(b.dropna()) | set(p.dropna())


def build_orbis_firm_year(force: bool = False) -> pd.DataFrame:
    """Stream ORBIS once, keep rows whose SD_ISIN is in the pay panel, dedup to
    one consolidated full-year row per (isin, year). Cached to BUILD_DIR.

    De-dup rule (data-review): NR_MONTHS==12, CONSCODE priority C1<C2<U1<U2,
    tie-break by largest TOAS.
    """
    if C.ORBIS_FIRM_YEAR_CACHE.exists() and not force:
        return pd.read_csv(C.ORBIS_FIRM_YEAR_CACHE)

    want = pay_isins()
    rows = []
    with open(C.ORBIS_CSV, "r", encoding=C.ORBIS_ENCODING,
              errors="replace", newline="") as fh:
        rdr = csv.reader(fh)
        header = next(rdr)
        idx = {h: i for i, h in enumerate(header)}
        keep_idx = {k: idx[k] for k in C.ORBIS_KEEP}
        si = idx["SD_ISIN"]
        for row in rdr:
            isin = row[si].strip().strip('"')
            if isin in want:
                rows.append([row[keep_idx[k]] for k in C.ORBIS_KEEP])

    o = pd.DataFrame(rows, columns=C.ORBIS_KEEP)
    o = o.rename(columns={"SD_ISIN": "isin", "CLOSDATE_year": "year"})
    o["isin"] = o["isin"].str.strip().str.strip('"')
    for c in ["OPRE", "ROA", "GEAR", "TOAS", "ROE", "SOLR", "PRMA", "EBTA",
              "EMPL", "ENVA", "NR_MONTHS"]:
        o[c] = pd.to_numeric(o[c].replace("", np.nan), errors="coerce")
    o["year"] = pd.to_numeric(o["year"], errors="coerce").astype("Int64")

    # full fiscal year only, then dedup
    o = o[o["NR_MONTHS"] == 12].copy()
    o["cprio"] = o["CONSCODE"].map(C.CONSCODE_PRIORITY).fillna(9)
    o = o.sort_values(["isin", "year", "cprio", "TOAS"],
                      ascending=[True, True, True, False])
    ded = o.drop_duplicates(["isin", "year"], keep="first").reset_index(drop=True)
    ded.to_csv(C.ORBIS_FIRM_YEAR_CACHE, index=False, encoding="utf-8")
    return ded


if __name__ == "__main__":
    # Inspect the raw inputs:  python -m src.loaders
    C.enable_utf8_stdout()
    board, person, attrs = load_board(), load_person(), load_person_attrs()
    print("[BOARD]  company_year.csv :", board.shape,
          "| years", int(board.year.min()), "-", int(board.year.max()),
          "| firms", board["isin"].nunique())
    print("         money columns end in _bt, e.g.:",
          [c for c in board.columns if c.endswith("_bt")][:6], "...")
    print("[PERSON] person_year.csv  :", person.shape,
          "| execs", person["exec_id"].nunique())
    print("[ATTR]   company_person.csv:", attrs.shape)
    print("\nStreaming + de-duplicating ORBIS (cached after first run)...")
    orbis = build_orbis_firm_year()
    print("[ORBIS] firm-year (deduped):", orbis.shape,
          "| firms", orbis["isin"].nunique(),
          "| OPRE present %.0f%%" % (100 * orbis["OPRE"].notna().mean()),
          "| consolidated %.0f%%" % (100 * orbis["CONSCODE"].isin(["C1", "C2"]).mean()))
