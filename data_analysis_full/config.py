"""Central configuration: paths, column specs, and the (external) CPI series.

All modelling choices are locked in the plan (exec_pay_full_guide.tex, Section 1).
This file is the single place where file locations and the few external inputs live.
"""
from __future__ import annotations
from pathlib import Path

# --- paths -----------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
BUILD_DIR = PROJECT_ROOT / "build"          # cached intermediates + outputs
BUILD_DIR.mkdir(exist_ok=True)

BOARD_CSV = DATA_DIR / "2008-2021" / "company_year.csv"
PERSON_CSV = DATA_DIR / "2008-2021" / "person_year.csv"
PERSON_ATTR_CSV = DATA_DIR / "2008-2021" / "company_person.csv"
ORBIS_CSV = DATA_DIR / "ORBIS_Abzug_DE_2005_2024.csv"

# Cached deduplicated ORBIS firm-year table (built once, ~15 s stream).
ORBIS_FIRM_YEAR_CACHE = BUILD_DIR / "orbis_firm_year.csv"

# --- file formats (discovered during the data review) ----------------------
PAY_SEP = "|"
PAY_ENCODING = "utf-8"          # the pay files are UTF-8 (latin-1/cp1252 mangle umlauts)
ORBIS_SEP = ","
ORBIS_ENCODING = "latin-1"      # ORBIS text cols unused; latin-1 never crashes

# --- locked variable spec (plan Section 1) ---------------------------------
SIZE = "opre"            # firm size  -> log()
PERF = "roa"             # performance control
LEVERAGE = "gear"        # leverage control
PAY = "total_comp"       # dependent (person) / total_comp_bt (board)

# RHS of every regression (Parts 1-4): log(opre) + roa + gear + year FE
RHS_NUMERIC = ["lopre", PERF, LEVERAGE]

# ORBIS columns we keep from the 286-column dump
ORBIS_KEEP = ["bvdid", "CONSCODE", "CLOSDATE_year", "NR_MONTHS", "SD_ISIN",
              "OPRE", "ROA", "GEAR", "TOAS", "ROE", "SOLR", "PRMA", "EBTA",
              "EMPL", "ENVA", "LISTED", "MAINEXCH", "ORIG_CURRENCY"]

# ORBIS de-dup: consolidation-code preference (consolidated first), then max TOAS
CONSCODE_PRIORITY = {"C1": 0, "C2": 1, "U1": 2, "U2": 3, "LF": 4}

# --- Part 3 buckets --------------------------------------------------------
# Six non-overlapping leaf buckets (plan eq. 7). Board columns add the _bt suffix.
BUCKETS_6 = ["salary", "one_year_bonus", "multi_year_bonus_grants",
             "stock_grants", "option_grants", "other_annual_comp"]

# Well-populated 3-bucket headline split (Fixed / STI / LTI). Values are the
# board (_bt) leaf columns that get summed into each headline bucket.
BUCKETS_3 = {
    "Fixed": ["salary", "other_annual_comp"],
    "STI":   ["one_year_bonus"],
    "LTI":   ["total_equity_grants", "multi_year_bonus_grants"],
}

DIVERGENCE_MIN_BUCKETS = 3      # require >=3 present before taking Var

# --- external input: German CPI / HICP -------------------------------------
# EXT in the plan. PLACEHOLDER values (Destatis VPI, 2015 = 100, annual avg,
# approximate) so the pipeline runs end-to-end. Replace with official Destatis
# numbers, or drop a `data/cpi_germany.csv` (columns: year,cpi) to override.
CPI_BASE_YEAR = 2015
CPI_GERMANY = {
    2005: 86.2, 2006: 87.6, 2007: 89.6, 2008: 91.9, 2009: 92.2, 2010: 92.5,
    2011: 94.0, 2012: 95.7, 2013: 97.1, 2014: 98.6, 2015: 100.0, 2016: 100.5,
    2017: 102.0, 2018: 103.8, 2019: 105.3, 2020: 105.8, 2021: 109.1,
    2022: 116.6, 2023: 123.6, 2024: 126.4,
}


def load_cpi() -> dict[int, float]:
    """Return {year: index}. Uses data/cpi_germany.csv if present, else the
    built-in placeholder."""
    override = DATA_DIR / "cpi_germany.csv"
    if override.exists():
        import csv
        out = {}
        with open(override, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                out[int(row["year"])] = float(row["cpi"])
        return out
    return dict(CPI_GERMANY)


def enable_utf8_stdout() -> None:
    """Make printing umlauts safe on the Windows console (used by the __main__
    demos below). Harmless if stdout has no buffer."""
    import sys, io
    if hasattr(sys.stdout, "buffer"):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


if __name__ == "__main__":
    # Inspect the locked configuration:  python -m src.config
    enable_utf8_stdout()
    print("PROJECT_ROOT:", PROJECT_ROOT)
    print("DATA_DIR    :", DATA_DIR)
    print("BUILD_DIR   :", BUILD_DIR)
    print("\nLocked spec -> size:", SIZE, "| perf:", PERF,
          "| leverage:", LEVERAGE, "| pay:", PAY)
    print("\n6 leaf buckets:", BUCKETS_6)
    print("\n3 headline buckets (Fixed/STI/LTI) are GROUPINGS of leaf columns:")
    for hb, leaves in BUCKETS_3.items():
        print(f"   {hb:6s} = {' + '.join(leaves)}")
    cpi = load_cpi()
    print(f"\nCPI: base year {CPI_BASE_YEAR}, covers "
          f"{min(cpi)}-{max(cpi)} ({len(cpi)} years)")
