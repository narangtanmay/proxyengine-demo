from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROJECT = ROOT.parent
DATA_DIR = PROJECT / "Data"
OUTPUT_DATA = ROOT / "outputs" / "data"
OUTPUT_FIGURES = ROOT / "outputs" / "figures"

BASE_YEAR = 2015

# Fixed number of fundamental peer clusters (K-Means)
N_PEER_CLUSTERS = 7

# Approximate German CPI (2015 = 100), Destatis-compatible scale
CPI_BY_YEAR = {
    2006: 91.8, 2007: 93.5, 2008: 96.5, 2009: 97.1, 2010: 98.5,
    2011: 100.2, 2012: 102.0, 2013: 103.4, 2014: 104.2, 2015: 105.0,
    2016: 105.2, 2017: 107.0, 2018: 108.8, 2019: 110.5, 2020: 111.0,
    2021: 114.5, 2022: 121.0, 2023: 125.5, 2024: 128.0,
}

PAY_BUCKETS = {
    "salary": "salary_bt",
    "one_year_bonus": "one_year_bonus_bt",
    "multi_year_grants": "multi_year_bonus_grants_bt",
    "stock_grants": "stock_grants_bt",
    "option_grants": "option_grants_bt",
    "other_annual": "other_annual_bt",
}

# Firm-level clustering features (fundamentals only — not index tier or pay)
ORBIS_CLUSTER_COLS = ["TOAS", "EMPL", "OPPL", "OPRE", "ROA", "GEAR"]

CLUSTER_FEATURE_LABELS = {
    "log_toas": "Total Assets (TOAS)",
    "turnover_per_empl": "Turnover per Employee",
    "log_empl": "Employees (EMPL)",
    "log_oppl": "Operating Profit (OPPL)",
    "log_opre": "Operating Revenue (OPRE)",
    "roa": "Return on Assets (ROA)",
    "gear": "Gearing (GEAR)",
}
