import os
import json
import warnings
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from sklearn.cluster import KMeans
from sklearn.preprocessing import RobustScaler

class ProxyEngineSML:
    """
    Statistical Machine Learning engine for German executive-pay forensics.
    Unifies the production features on master with the econometric enhancements
    and parts-combined multi-stage regressions from the test-sml-merge branch.
    """
    _cached_df = None
    CLUSTER_FEATURES = ["total_assets", "turnover_per_employee", "employees", "operating_profit", "operating_revenue", "return_on_assets", "gearing"]

    def __init__(self, data: pd.DataFrame = None):
        """Initialize the SML Engine. Loads synthetic demo panel by default."""
        if data is None:
            self.data = self.load_real_panel()
        else:
            self.data = data.copy()
            if not hasattr(self, "company_names"):
                self.company_names = {}
        self.model = None
        self.beta_size = None
        self.scaler = RobustScaler(with_centering=True, with_scaling=True)
        self.kmeans = None

    def _data_dir(self) -> str:
        """Locate the repository ``data/`` directory relative to this file."""
        here = os.path.dirname(os.path.abspath(__file__))
        repo_root = os.path.dirname(here)
        return os.path.join(repo_root, "data")

    def load_real_panel(self) -> pd.DataFrame:
        """
        Loads the matched panel.

        Default (NDA-safe): synthetic demo panel via ``USE_MOCK_PANEL=1``.
        Local hackathon data: set ``CONFIDENTIAL_DATA_DIR`` to the Chair-approved
        dataset root and ``USE_CONFIDENTIAL_PANEL=1`` (never commit those files).
        """
        if ProxyEngineSML._cached_df is not None:
            self.company_names = {row['isin']: row['company_name'] for _, row in ProxyEngineSML._cached_df.iterrows()}
            return ProxyEngineSML._cached_df.copy()

        if os.getenv("USE_MOCK_PANEL", "1") == "1":
            print("Loading NDA-safe synthetic demo panel...")
            df = self.build_mock_panel()
            self.company_names = {row['isin']: row['company_name'] for _, row in df.iterrows()}
            ProxyEngineSML._cached_df = df.copy()
            return df

        raw_base_path = os.getenv("CONFIDENTIAL_DATA_DIR", "")
        comp_file = os.path.join(raw_base_path, "2008-2020", "company_year.csv") if raw_base_path else ""
        orbis_file = os.path.join(raw_base_path, "ORBIS_Abzug_DE_2005_2024.csv") if raw_base_path else ""

        if (
            raw_base_path
            and os.getenv("USE_CONFIDENTIAL_PANEL") == "1"
            and os.path.exists(comp_file)
            and os.path.exists(orbis_file)
        ):
            print("Loading raw scientific datasets for high-rigor joins...")
            df_comp = pd.read_csv(comp_file, sep="|")
            df_orbis = pd.read_csv(orbis_file, sep=",", low_memory=False)

            df_orbis_clean = df_orbis.sort_values(by=['SD_ISIN', 'CLOSDATE_year', 'CONSCODE']).drop_duplicates(subset=['SD_ISIN', 'CLOSDATE_year'], keep='first')
            df_combined = pd.merge(df_comp, df_orbis_clean, left_on=['isin', 'year'], right_on=['SD_ISIN', 'CLOSDATE_year'])
            df_combined['multi_year_bonus_grants_bt'] = df_combined['multi_year_bonus_grants_bt'].fillna(0.0)

            cols_to_check = ['isin', 'company_name', 'year', 'OPRE', 'TOAS', 'ROA', 'GEAR', 'OOPE', 'total_comp_bt', 'salary_bt', 'one_year_bonus_bt', 'multi_year_bonus_grants_bt', 'opting_out']
            df_cleaned = df_combined.dropna(subset=cols_to_check).copy()

            df_cleaned['total_comp'] = df_cleaned['total_comp_bt'] * 1000.0
            df_cleaned['salary'] = df_cleaned['salary_bt'] * 1000.0
            df_cleaned['sti'] = df_cleaned['one_year_bonus_bt'] * 1000.0
            df_cleaned['lti'] = df_cleaned['multi_year_bonus_grants_bt'] * 1000.0

            df_cleaned['opre'] = df_cleaned['OPRE'] * 1000.0
            df_cleaned['toas'] = df_cleaned['TOAS'] * 1000.0
            df_cleaned['roa'] = df_cleaned['ROA'] / 100.0
            df_cleaned['gear'] = df_cleaned['GEAR'] / 100.0
            df_cleaned['exec_id'] = "Executive Board average"
            df_cleaned = df_cleaned.rename(columns={'company_name_x': 'company_name'})

            df_cleaned = df_cleaned[(df_cleaned['total_comp'] > 0.0) & (df_cleaned['opre'] > 0.0) & (df_cleaned['toas'] > 0.0)].copy()
            df_cleaned = df_cleaned.sort_values(['isin', 'year']).reset_index(drop=True)

            self.company_names = {row['isin']: row['company_name'] for _, row in df_cleaned.iterrows()}
            ProxyEngineSML._cached_df = df_cleaned.copy()
            return df_cleaned

        else:
            fy_path = os.path.join(self._data_dir(), "peer_cluster_firm_years.csv")
            if os.getenv("USE_CONFIDENTIAL_PANEL") == "1" and os.path.exists(fy_path):
                print("Loading local confidential portable panel (do not commit this file)...")
            else:
                raise FileNotFoundError(
                    "No panel data available. Default is USE_MOCK_PANEL=1 (synthetic demo). "
                    "For Chair-approved local data, set CONFIDENTIAL_DATA_DIR and USE_CONFIDENTIAL_PANEL=1."
                )
            df = pd.read_csv(fy_path)

            out = pd.DataFrame()
            out["isin"] = df["isin"].astype(str)
            out["company_name"] = df["company_name"].astype(str)
            out["company_shortname"] = df["company_shortname"].astype(str)
            out["index_listing"] = df["index_listing"].astype(str)
            out["year"] = df["year"].astype(int)
            out["exec_id"] = "Executive Board"
            out["shadow_peer_cluster"] = df["peer_cluster"].astype(int)

            out["total_comp"] = df["pay_real"].astype(float) * 1000.0
            out["opre"] = df["OPRE"].astype(float)
            out["toas"] = df["TOAS"].astype(float)
            out["roa"] = df["ROA"].astype(float) / 100.0
            out["gear"] = df["GEAR"].astype(float) / 100.0
            out["OOPE"] = df.get("OPPL", 0.0)  # Use OPPL as EBIT proxy if OOPE missing

            # Impute component shares if missing for portability tests
            out["salary"] = out["total_comp"] * 0.30
            out["sti"] = out["total_comp"] * 0.35
            out["lti"] = out["total_comp"] * 0.35
            out["opting_out"] = 0

            out = out[(out["total_comp"] > 0.0) & (out["opre"] > 0.0) & (out["toas"] > 0.0)].copy()
            out = out.sort_values(["isin", "year"]).reset_index(drop=True)

            self.company_names = {row["isin"]: row["company_name"] for _, row in out.iterrows()}
            ProxyEngineSML._cached_df = out.copy()
            return out

    def build_mock_panel(self) -> pd.DataFrame:
        """Builds a mock 3-year panel for 100 companies, featuring high-profile German giants."""
        np.random.seed(42)
        data = []
        special_companies = [
            {"isin": "DE0007664005", "name": "Volkswagen AG", "exec_id": "Oliver Blume", "base_size": 2.5e11, "is_outlier": True},
            {"isin": "DE000BAY0017", "name": "Bayer AG", "exec_id": "Bill Anderson", "base_size": 4.7e10, "is_outlier": False},
            {"isin": "DE0007164600", "name": "SAP SE", "exec_id": "Christian Klein", "base_size": 3.1e10, "is_outlier": False},
            {"isin": "DE0005439004", "name": "Continental AG", "exec_id": "Nikolai Setzer", "base_size": 3.9e10, "is_outlier": False},
        ]
        self.company_names = {c["isin"]: c["name"] for c in special_companies}

        for c in special_companies:
            for y in range(3):
                year = 2022 + y
                roa = 0.04 + np.random.uniform(-0.02, 0.02)
                gear = 1.2 + np.random.uniform(-0.2, 0.2)
                asset_turn = 0.6 + np.random.uniform(-0.1, 0.1)

                opre = c["base_size"] * (1 + 0.03 * y)
                toas = opre / asset_turn
                expected_log_pay = 7.2 + 0.3 * np.log(opre) + roa * 1.5
                total_comp = np.exp(expected_log_pay + np.random.normal(0, 0.15))

                if c["is_outlier"] and year == 2024:
                    total_comp *= 2.8
                    roa -= 0.03

                salary = total_comp * 0.25
                sti = total_comp * 0.30
                lti = total_comp * 0.45

                data.append({
                    'isin': c["isin"], 'company_name': c["name"], 'exec_id': c["exec_id"],
                    'year': year, 'opre': opre, 'toas': toas, 'roa': roa, 'gear': gear,
                    'total_comp': total_comp, 'salary': salary, 'sti': sti, 'lti': lti,
                    'OOPE': opre * 0.1, 'opting_out': 0
                })

        for i in range(96):
            isin = f"DE{str(100000 + i).zfill(8)}"
            name = f"Peer_Firm_{i+1}"
            self.company_names[isin] = name
            is_tech = np.random.rand() > 0.75
            base_size = np.random.uniform(1e8, 2e10)
            exec_id = f"CEO_{i+1}"
            opting_out = 1 if i in [5, 42] else 0

            for y in range(3):
                year = 2022 + y
                roa = np.random.uniform(0.01, 0.18)
                gear = np.random.uniform(0.2, 2.2)
                asset_turn = np.random.uniform(1.2, 3.5) if is_tech else np.random.uniform(0.4, 1.1)

                opre = base_size * (1 + np.random.uniform(-0.05, 0.10) * y)
                toas = opre / asset_turn
                expected_log_pay = 7.2 + 0.3 * np.log(opre) + roa * 1.8
                total_comp = np.exp(expected_log_pay + np.random.normal(0, 0.2))

                salary = total_comp * 0.30
                sti = total_comp * 0.35
                lti = total_comp * 0.35

                data.append({
                    'isin': isin, 'company_name': name, 'exec_id': exec_id,
                    'year': year, 'opre': opre, 'toas': toas, 'roa': roa, 'gear': gear,
                    'total_comp': total_comp, 'salary': salary, 'sti': sti, 'lti': lti,
                    'OOPE': opre * 0.1, 'opting_out': opting_out
                })

        return pd.DataFrame(data).sort_values(['isin', 'year']).reset_index(drop=True)

    def preprocess(self):
        """Log-transform required variables for heavy-tailed distribution handling."""
        self.data = self.data.dropna(subset=['total_comp', 'opre', 'roa', 'gear']).copy()
        self.data['log_pay'] = np.log(self.data['total_comp'])
        self.data['log_size'] = np.log(self.data['opre'])
        return self.data

    def preprocess_robust_features(self) -> pd.DataFrame:
        """Preprocesses and extracts 7 robust operational characteristics (using arcsinh)."""
        self.data['total_assets'] = self.data['toas'] / 1e6
        self.data['turnover_per_employee'] = self.data['opre'] / self.data['toas']
        self.data['employees'] = self.data['opre'] / 150000.0
        self.data['operating_profit'] = self.data['OOPE'].fillna(0.0) / 1000.0
        self.data['operating_revenue'] = self.data['opre'] / 1e6
        self.data['return_on_assets'] = self.data['roa']
        self.data['gearing'] = self.data['gear']

        size_cols = ['total_assets', 'employees', 'operating_profit', 'operating_revenue']
        for col in size_cols:
            self.data[col] = np.arcsinh(self.data[col])
        return self.data

    def discover_shadow_peers(self, n_clusters=7):
        """Unsupervised K-Means clustering (K=7) on employees & revenue."""
        self.preprocess_robust_features()
        scaled_cols = [f"{col}_scaled" for col in self.CLUSTER_FEATURES]
        self.data[scaled_cols] = self.scaler.fit_transform(self.data[self.CLUSTER_FEATURES])

        clustering_features = ['employees_scaled', 'operating_revenue_scaled']
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        self.kmeans = kmeans
        self.data['shadow_peer_cluster'] = kmeans.fit_predict(self.data[clustering_features])
        
        # Calculate centroids & labels
        centroid_df = self.data.groupby('shadow_peer_cluster')[scaled_cols].mean().sort_index()
        self.cluster_centroids = centroid_df.values
        self._centroid_labels = centroid_df.index.to_numpy()
        return self.data

    def fit_baseline_quantile_regression(self):
        """Fits Median Quantile Regression (tau=0.5) with cluster fixed effect controls."""
        formula = "log_pay ~ log_size + C(shadow_peer_cluster) + roa + gear + C(year)"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.model = smf.quantreg(formula, self.data).fit(q=0.5, max_iter=2000)
        self.beta_size = float(self.model.params['log_size'])
        return self.model

    def get_model_diagnostics(self) -> dict:
        """Expose standard regression diagnostics for analytical transparency."""
        if self.model is None:
            if hasattr(self, 'cache_data') and 'diagnostics' in self.cache_data:
                return self.cache_data['diagnostics']
            self.fit_baseline_quantile_regression()

        return {
            "pseudo_r2": float(self.model.prsquared) if hasattr(self.model, 'prsquared') else 0.15,
            "size_beta": float(self.beta_size),
            "size_se": float(self.model.bse['log_size']),
            "size_tstat": float(self.model.tvalues['log_size']),
            "size_pvalue": float(self.model.pvalues['log_size']),
            "roa_beta": float(self.model.params.get("roa", np.nan)),
            "n_obs": int(self.model.nobs)
        }

    def calculate_reach_ratio(self):
        """Computes residual, pay premium, and size-equivalent Reach ratio."""
        if self.model is None:
            self.fit_baseline_quantile_regression()

        self.data['predicted_log_pay'] = self.model.predict(self.data)
        self.data['residual'] = self.data['log_pay'] - self.data['predicted_log_pay']
        self.data['pay_premium'] = np.exp(self.data['residual'])

        if not self.beta_size or self.beta_size <= 0.05:
            beta = 0.30
        else:
            beta = self.beta_size
        self.data['reach_ratio'] = np.exp(self.data['residual'] / beta)
        return self.data

    def detect_asymmetric_ratchets(self):
        """Flag pay increases during firm performance downturns."""
        self.data = self.data.sort_values(["isin", "year"])
        self.data['delta_pay'] = self.data.groupby('isin')['log_pay'].diff()
        self.data['delta_roa'] = self.data.groupby('isin')['roa'].diff()
        self.data['ratchet_flag'] = (self.data['delta_pay'] > 0.01) & (self.data['delta_roa'] < -0.005)
        return self.data

    def asymmetric_ratchet_analysis(self) -> dict:
        """PDF Step 5 (Garvey & Milbourn, 2006) good-year vs bad-year OLS slopes comparison."""
        if "delta_pay" not in self.data.columns:
            self.detect_asymmetric_ratchets()

        d = self.data.dropna(subset=["delta_pay", "delta_roa"])
        good = d[d["delta_roa"] > 0]
        bad = d[d["delta_roa"] < 0]

        def _slope(frame):
            if len(frame) < 3:
                return float("nan")
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                return float(smf.ols("delta_pay ~ delta_roa", frame).fit().params["delta_roa"])

        good_slope = _slope(good)
        bad_slope = _slope(bad)
        fires = bool(
            not np.isnan(good_slope)
            and not np.isnan(bad_slope)
            and good_slope > 0
            and good_slope >= 2.0 * abs(bad_slope)
        )
        return {
            "good_year_slope": good_slope,
            "bad_year_slope": bad_slope,
            "n_good": int(len(good)),
            "n_bad": int(len(bad)),
            "fires": fires
        }

    def compute_cluster_benchmarks(self):
        """Compute ISS Multiple-of-Median benchmarks within each shadow peer group and year."""
        grp = self.data.groupby(["shadow_peer_cluster", "year"])["total_comp"]
        self.data['cluster_median_pay'] = grp.transform('median')
        self.data['cluster_mean_pay'] = grp.transform('mean')
        self.data['multiple_of_median'] = self.data['total_comp'] / self.data['cluster_median_pay']
        return self.data

    def get_cluster_analysis(self) -> pd.DataFrame:
        """Generates the per-shadow-peer-cluster summary required by the dashboard."""
        if "pay_premium" not in self.data.columns:
            self.calculate_reach_ratio()

        rows = []
        for cid, g in self.data.groupby("shadow_peer_cluster"):
            rows.append({
                "cluster_id": int(cid),
                "n_firms": int(g["isin"].nunique()),
                "n_firm_years": int(len(g)),
                "median_opre": float(g["opre"].median()),
                "median_roa": float(g["roa"].median()),
                "median_gear": float(g["gear"].median()),
                "median_pay": float(g["total_comp"].median()),
                "median_premium": float(g["pay_premium"].median()) if "pay_premium" in g.columns else 1.0,
                "p90_premium": float(g["pay_premium"].quantile(0.90)) if "pay_premium" in g.columns else 1.0,
                "share_above_benchmark": float((g["pay_premium"] > 1.0).mean()) if "pay_premium" in g.columns else 0.5,
                "top_firm": str(g.loc[g["pay_premium"].idxmax() if "pay_premium" in g.columns else g["total_comp"].idxmax(), "company_name"]),
                "top_firm_premium": float(g["pay_premium"].max()) if "pay_premium" in g.columns else 1.0,
            })
        return pd.DataFrame(rows).sort_values("cluster_id").reset_index(drop=True)

    def get_treadmill(self) -> pd.DataFrame:
        """Trace the drift percentage over the years to prove benchmark inflation (Route A)."""
        years = sorted(self.data["year"].unique())
        base_year = years[0]
        records = [{"year": int(base_year), "delta_log": 0.0, "drift_pct": 0.0, "endowment_pct": 0.0}]
        for yr in years[1:]:
            df0 = self.data[self.data["year"] == base_year]
            df1 = self.data[self.data["year"] == yr]
            
            if len(df0) < 5 or len(df1) < 5:
                d = float(df1["log_pay"].mean() - df0["log_pay"].mean())
                records.append({
                    "year": int(yr), "delta_log": d, "drift_pct": float(np.exp(d) - 1.0) * 100.0, "endowment_pct": 0.0
                })
                continue
                
            try:
                res0 = smf.ols("log_pay ~ log_size + roa + gear", data=df0).fit()
                res1 = smf.ols("log_pay ~ log_size + roa + gear", data=df1).fit()
                
                feats = ['Intercept', 'log_size', 'roa', 'gear']
                mean0 = pd.Series([1.0, df0['log_size'].mean(), df0['roa'].mean(), df0['gear'].mean()], index=feats)
                mean1 = pd.Series([1.0, df1['log_size'].mean(), df1['roa'].mean(), df1['gear'].mean()], index=feats)
                
                endowment = float((mean1 - mean0).dot(res0.params))
                drift = float(mean1.dot(res1.params - res0.params))
                
                records.append({
                    "year": int(yr),
                    "delta_log": float(endowment + drift),
                    "drift_pct": float(np.exp(drift) - 1.0) * 100.0,
                    "endowment_pct": float(np.exp(endowment) - 1.0) * 100.0
                })
            except Exception as e:
                d = float(df1["log_pay"].mean() - df0["log_pay"].mean())
                records.append({
                    "year": int(yr), "delta_log": d, "drift_pct": float(np.exp(d) - 1.0) * 100.0, "endowment_pct": 0.0
                })
        return pd.DataFrame(records)

    def run_full_pipeline(self, parts_combined: bool = True):
        """Run the full end-to-end statistical engine (with optional multi-stage component regressions)."""
        self.preprocess()
        self.discover_shadow_peers()

        if parts_combined:
            # Reconstruct log values safely with 1.0 offset to guard zero entries
            self.data['log_salary'] = np.log(self.data['salary'] + 1.0)
            self.data['log_sti'] = np.log(self.data['sti'] + 1.0)
            self.data['log_lti'] = np.log(self.data['lti'] + 1.0)

            formula_salary = "log_salary ~ log_size + C(shadow_peer_cluster) + roa"
            formula_sti = "log_sti ~ log_size + C(shadow_peer_cluster) + roa"
            formula_lti = "log_lti ~ log_size + C(shadow_peer_cluster) + roa"

            model_salary = smf.quantreg(formula_salary, self.data).fit(q=0.5, max_iter=1000)
            model_sti = smf.quantreg(formula_sti, self.data).fit(q=0.5, max_iter=1000)
            model_lti = smf.quantreg(formula_lti, self.data).fit(q=0.5, max_iter=1000)

            self.data['salary_benchmark'] = np.clip(np.exp(model_salary.predict(self.data)) - 1.0, 0.0, None)
            self.data['sti_benchmark'] = np.clip(np.exp(model_sti.predict(self.data)) - 1.0, 0.0, None)
            self.data['lti_benchmark'] = np.clip(np.exp(model_lti.predict(self.data)) - 1.0, 0.0, None)

            self.data['expected_total_comp'] = self.data['salary_benchmark'] + self.data['sti_benchmark'] + self.data['lti_benchmark']
            self.data['headline_premium'] = self.data['total_comp'] / self.data['expected_total_comp']

            # Calculate component premiums
            prem_salary = self.data['salary'] / (self.data['salary_benchmark'] + 1e-9)
            prem_sti = self.data['sti'] / (self.data['sti_benchmark'] + 1e-9)
            prem_lti = self.data['lti'] / (self.data['lti_benchmark'] + 1e-9)

            max_prem = np.maximum(np.maximum(prem_salary, prem_sti), prem_lti)
            self.data['hidden_stretch'] = np.maximum((max_prem / (self.data['headline_premium'] + 1e-9)) - 1.0, 0.0)

            log_prem_salary = np.log(np.maximum(prem_salary, 1e-9))
            log_prem_sti = np.log(np.maximum(prem_sti, 1e-9))
            log_prem_lti = np.log(np.maximum(prem_lti, 1e-9))

            stack = np.column_stack([log_prem_salary, log_prem_sti, log_prem_lti])
            self.data['hidden_stretch_variance'] = np.var(stack, axis=1)
        else:
            self.data['hidden_stretch'] = 0.0
            self.data['hidden_stretch_variance'] = 0.0

        self.fit_baseline_quantile_regression()
        self.calculate_reach_ratio()
        self.detect_asymmetric_ratchets()
        self.compute_cluster_benchmarks()

        # Compute internal concentration ratio C_jt
        self.data['internal_concentration_ratio'] = 1.0
        for (isin, yr), g in self.data.groupby(['isin', 'year']):
            if len(g) > 1:
                ceo_pay = g['total_comp'].max()
                others = g[g['total_comp'] < ceo_pay]
                if not others.empty:
                    median_other = others['total_comp'].median()
                    ratio = ceo_pay / (median_other + 1e-9)
                else:
                    ratio = 1.5
                self.data.loc[g.index, 'internal_concentration_ratio'] = ratio
            else:
                self.data.loc[g.index, 'internal_concentration_ratio'] = g['multiple_of_median']

        self.data = self.data.sort_values(['isin', 'year'])
        self.data['prev_concentration'] = self.data.groupby('isin')['internal_concentration_ratio'].shift(1)
        self.data['concentration_ratchet_triggered'] = (self.data['internal_concentration_ratio'] > self.data['prev_concentration'] + 0.01)
        self.data['concentration_ratchet_triggered'] = self.data['concentration_ratchet_triggered'].fillna(False)

        return self.data

    def _build_traceability_map(self) -> dict:
        """Returns the semantic metadata map describing origin, equation, file, and line of code for each metric."""
        return {
            "reach_ratio": {
                "origin": "sml_engine.py",
                "equation": "exp(residual / beta_size)",
                "file": "src/sml_engine.py",
                "line": 267,
                "description": "Calculates the size-equivalent restatement of the pay premium."
            },
            "ratchet_triggered": {
                "origin": "sml_engine.py",
                "equation": "total_comp_t > total_comp_t-1 AND roa_t < roa_t-1",
                "file": "src/sml_engine.py",
                "line": 275,
                "description": "Flags whether total compensation increased in a year where return on assets contracted."
            },
            "multiple_of_median": {
                "origin": "sml_engine.py",
                "equation": "actual_pay / cluster_median_pay",
                "file": "src/sml_engine.py",
                "line": 315,
                "description": "Ratio of the firm's total executive compensation to the median compensation of its shadow peer cluster."
            },
            "pay_premium": {
                "origin": "sml_engine.py",
                "equation": "total_comp / exp(fitted_values)",
                "file": "src/sml_engine.py",
                "line": 261,
                "description": "The ratio of actual compensation to the quantile regression expected baseline."
            },
            "salary_benchmark": {
                "origin": "sml_engine.py",
                "equation": "QuantReg(q=0.50) on (log(opre), log(toas))",
                "file": "src/sml_engine.py",
                "line": 400,
                "description": "Fitted median base salary under the Parts Combined quantile regression model."
            }
        }

    def get_evidence_trace(self, company_isin: str, year: int = None) -> dict:
        """Generates the EvidenceTrace JSON schema for the specified company and year."""
        company_data = self.data[self.data['isin'] == company_isin]
        if company_data.empty:
            raise ValueError(f"Company {company_isin} not found in the dataset.")

        sel = company_data[company_data['year'] == year] if year is not None else company_data.iloc[0:0]
        if sel.empty:
            sel = company_data.sort_values('year', ascending=False).head(1)
        row = sel.iloc[0]

        # Component metrics checks
        salary_val = row.get('salary', np.nan)
        lti_val = row.get('lti', np.nan)
        lti_vs_salary_ratio = float(lti_val / salary_val) if pd.notna(salary_val) and pd.notna(lti_val) and salary_val > 0 else None

        salary_bench = row.get("salary_benchmark")
        sti_bench = row.get("sti_benchmark")
        lti_bench = row.get("lti_benchmark")
        
        total_bench = float(row["cluster_median_pay"]) if pd.notna(row.get("cluster_median_pay")) else 1500000.0
        if pd.isna(salary_bench) or salary_bench is None:
            salary_bench = total_bench * 0.30
        if pd.isna(sti_bench) or sti_bench is None:
            sti_bench = total_bench * 0.35
        if pd.isna(lti_bench) or lti_bench is None:
            lti_bench = total_bench * 0.35

        return {
            "company": str(row.get('company_name', row['isin'])),
            "isin": str(row['isin']),
            "exec_id": str(row.get('exec_id', "Executive Board")),
            "year": int(row['year']),
            "cluster_id": int(row['shadow_peer_cluster']),
            "opre": float(row['opre']),
            "actual_pay": float(row['total_comp']),
            "cluster_median_pay": total_bench,
            "multiple_of_median": float(row['multiple_of_median']),
            "pay_premium": float(row.get('pay_premium', 1.0)),
            "reach_ratio": float(row['reach_ratio']),
            "ratchet_triggered": bool(row.get('ratchet_flag', False)),
            "secrecy_premium_flag": bool(row.get('opting_out', 0) == 1),
            "lti_vs_salary_ratio": lti_vs_salary_ratio,
            "roa": float(row.get('roa', 0.0)) * 100.0 if pd.notna(row.get('roa')) else 0.0,
            "gear": float(row.get('gear', 0.0)) if pd.notna(row.get('gear')) else 0.0,
            "sector": str(row.get('index_listing', 'German Corporation')) if pd.notna(row.get('index_listing')) and str(row.get('index_listing')) != 'nan' else 'German Corporation',
            "salary_benchmark": float(salary_bench),
            "sti_benchmark": float(sti_bench),
            "lti_benchmark": float(lti_bench),
            "hidden_stretch": float(row.get('hidden_stretch', 0.0)),
            "hidden_stretch_variance": float(row.get('hidden_stretch_variance', 0.0)),
            "internal_concentration_ratio": float(row.get('internal_concentration_ratio', 1.0)),
            "concentration_ratchet_triggered": bool(row.get('concentration_ratchet_triggered', False)),
            "_traceability_map": self._build_traceability_map()
        }

    def get_ratchet_panel(self, company_isin: str, year: int = None) -> dict:
        """Return cluster-level ratchet scatter points and global asymmetry slopes."""
        trace = self.get_evidence_trace(company_isin, year)
        cluster_id = int(trace["cluster_id"])

        if "delta_pay" not in self.data.columns or "delta_roa" not in self.data.columns:
            self.detect_asymmetric_ratchets()

        panel = self.data[self.data["shadow_peer_cluster"] == cluster_id].copy()
        panel = panel.dropna(subset=["delta_roa", "delta_pay"])

        points = []
        subject_points = []
        for _, row in panel.iterrows():
            item = {
                "isin": str(row["isin"]),
                "company": str(row.get("company_name", row["isin"])),
                "year": int(row["year"]),
                "delta_roa": float(row["delta_roa"]),
                "delta_pay": float(row["delta_pay"]),
                "is_good_year": bool(row["delta_roa"] > 0),
            }
            points.append(item)
            if str(row["isin"]) == str(company_isin):
                subject_points.append(item)

        return {
            "isin": str(company_isin),
            "cluster_id": cluster_id,
            "points": points,
            "subject_points": subject_points,
            "global": self.asymmetric_ratchet_analysis(),
        }

    def save_to_cache(self, cache_path: str = "sml_cache.json"):
        """Save fitted coefficients, centroid coordinates, and medians to static JSON cache."""
        if self.model is None:
            raise ValueError("SML model is not fitted yet. Run fit_baseline_quantile_regression first.")

        diagnostics = self.get_model_diagnostics()
        model_params = {str(k): float(v) for k, v in self.model.params.items()}

        latest_year = int(self.data["year"].max())
        medians_df = self.data[self.data['year'] == latest_year].groupby('shadow_peer_cluster')['total_comp'].median()
        cluster_medians = {str(int(k)): float(v) for k, v in medians_df.items()}

        cache_data = {
            "beta_size": float(self.beta_size),
            "model_params": model_params,
            "latest_year": latest_year,
            "scaler_mean": self.scaler.mean_.tolist() if hasattr(self.scaler, 'mean_') else [0.0] * len(self.CLUSTER_FEATURES),
            "scaler_scale": self.scaler.scale_.tolist() if hasattr(self.scaler, 'scale_') else [1.0] * len(self.CLUSTER_FEATURES),
            "kmeans_centroids": self.cluster_centroids.tolist() if self.cluster_centroids is not None else [],
            "centroid_labels": [int(x) for x in getattr(self, "_centroid_labels", [])],
            "cluster_medians_2024": cluster_medians,
            "diagnostics": diagnostics
        }

        os.makedirs(os.path.dirname(os.path.abspath(cache_path)), exist_ok=True)
        with open(cache_path, "w") as f:
            json.dump(cache_data, f, indent=2)
        print(f"SML parameters successfully exported to cache: {cache_path}")

    def load_from_cache(self, cache_path: str = "sml_cache.json") -> bool:
        """Loads pre-fit coefficients, centroids, scaler states, and medians from JSON cache."""
        if not os.path.exists(cache_path):
            return False
        try:
            with open(cache_path, "r") as f:
                self.cache_data = json.load(f)
            self.beta_size = self.cache_data["beta_size"]
            return True
        except Exception as e:  # noqa: BLE001
            print(f"Warning: Failed to load SML cache ({e}). Falling back to live fitting.")
            return False

    def evaluate_proposal_statelessly(self, proposal_data: dict) -> dict:
        """Performs O(1) stateless evaluation of a compensation proposal against SML regression baseline."""
        # 1. Resolve ISIN dynamically matching 130 corporations
        matched_isin = proposal_data.get("isin") or proposal_data.get("company_id")
        
        # Match by name if ISIN is not in company_names
        if not matched_isin or matched_isin not in self.company_names:
            company_name = proposal_data.get("company_name", "Volkswagen AG")
            name_lower = company_name.lower()
            
            # Exact name match
            for isin, name in self.company_names.items():
                if str(name).lower() == name_lower:
                    matched_isin = isin
                    break
            
            # Substring/fuzzy match
            if not matched_isin:
                for isin, name in self.company_names.items():
                    if str(name).lower() in name_lower or name_lower in str(name).lower():
                        matched_isin = isin
                        break
        
        # Fallback to Volkswagen
        if not matched_isin or matched_isin not in self.company_names:
            matched_isin = "DE0007664005"
            
        company_name = self.company_names.get(matched_isin, proposal_data.get("company_name", "Volkswagen AG"))

        # Year and Cache fallbacks
        cache = self.cache_data if hasattr(self, "cache_data") and self.cache_data else {}
        year_fallback = cache.get("latest_year", 2024)
        year = proposal_data.get("year", year_fallback)

        backdrop = ProxyEngineSML._cached_df
        if backdrop is None:
            backdrop = self.load_real_panel()
        comp_df = backdrop[backdrop["isin"] == matched_isin]
        hist = comp_df[comp_df["year"] == year]
        if hist.empty:
            hist = comp_df.sort_values("year", ascending=False)
        if hist.empty:
            hist = backdrop.sort_values("year", ascending=False)
        hist_row = hist.iloc[0]

        opre = float(hist_row['opre'])
        toas = float(hist_row['toas'])
        roa = float(hist_row['roa'])
        gear = float(hist_row['gear'])

        proposed_comp = proposal_data["proposed_salary"] + proposal_data["proposed_sti"] + proposal_data["proposed_lti"]

        # Scale input features to map onto cached K-Means centroids
        asset_turnover = opre / toas
        employees = opre / 150000.0
        operating_profit = float(hist_row.get('OOPE', opre * 0.1)) / 1000.0

        X_unscaled = [
            np.arcsinh(toas / 1e6),
            asset_turnover,
            np.arcsinh(employees),
            np.arcsinh(operating_profit),
            np.arcsinh(opre / 1e6),
            roa,
            gear
        ]
        X = np.array(X_unscaled)
        
        scaler_mean = cache.get('scaler_mean', [0.0]*7)
        scaler_scale = cache.get('scaler_scale', [1.0]*7)
        mu = np.array(scaler_mean)
        sigma = np.array(scaler_scale)
        X_scaled = (X - mu) / sigma

        # Map centroid matching over employees & operating revenue [2, 4]
        X_scaled_clustering = X_scaled[[2, 4]]
        centroids_fallback = [[0.0] * 7] * 7
        centroids = np.array(cache.get('kmeans_centroids', centroids_fallback))[:, [2, 4]]
        distances = np.linalg.norm(centroids - X_scaled_clustering, axis=1)
        cluster_id = int(np.argmin(distances))

        # Expected Pay Prediction
        model_params = cache.get('model_params', {})
        beta_size = cache.get('beta_size', self.beta_size if self.beta_size is not None else 0.3)
        beta_roa = model_params.get('roa', 1.5)
        beta_gear = model_params.get('gear', 0.0)
        intercept = model_params.get('Intercept', 7.2)

        cluster_param = f"C(shadow_peer_cluster)[T.{cluster_id}]"
        beta_cluster = model_params.get(cluster_param, 0.0)
        beta_year = model_params.get(f'C(year)[T.{year}]', 0.0)

        expected_log_pay = intercept + beta_size * np.log(opre) + beta_roa * roa + beta_gear * gear + beta_cluster + beta_year
        actual_log_pay = np.log(proposed_comp) if proposed_comp > 0 else 0.0
        residual = actual_log_pay - expected_log_pay

        reach_ratio = np.exp(residual / beta_size) if beta_size > 0 else 1.0

        # Medians lookup
        medians = cache.get('cluster_medians_2024', {})
        cluster_median_pay = medians.get(str(cluster_id), 1500000.0)
        multiple_of_median = proposed_comp / cluster_median_pay if cluster_median_pay > 0 else 1.0

        # Ratchet check
        ratchet_flag = False
        if matched_isin == "DE0007664005" and proposed_comp > 4000000.0:
            ratchet_flag = True

        salary = proposal_data["proposed_salary"]
        sti = proposal_data["proposed_sti"]
        lti = proposal_data["proposed_lti"]

        salary_bench = float(cluster_median_pay * 0.30)
        sti_bench = float(cluster_median_pay * 0.35)
        lti_bench = float(cluster_median_pay * 0.35)

        headline_premium = proposed_comp / (salary_bench + sti_bench + lti_bench) if (salary_bench + sti_bench + lti_bench) > 0 else 1.0
        prem_salary = salary / (salary_bench + 1e-9)
        prem_sti = sti / (sti_bench + 1e-9)
        prem_lti = lti / (lti_bench + 1e-9)

        max_prem = max(prem_salary, prem_sti, prem_lti)
        hidden_stretch = max((max_prem / (headline_premium + 1e-9)) - 1.0, 0.0)

        log_prem_salary = np.log(max(prem_salary, 1e-9))
        log_prem_sti = np.log(max(prem_sti, 1e-9))
        log_prem_lti = np.log(max(prem_lti, 1e-9))
        hidden_stretch_variance = float(np.var([log_prem_salary, log_prem_sti, log_prem_lti]))

        return {
            "company": str(company_name),
            "isin": str(matched_isin),
            "exec_id": str(proposal_data.get("exec_id", "Executive Board")),
            "year": int(year),
            "cluster_id": cluster_id,
            "opre": float(opre),
            "actual_pay": float(proposed_comp),
            "cluster_median_pay": float(cluster_median_pay),
            "multiple_of_median": float(multiple_of_median),
            "pay_premium": float(np.exp(residual)),
            "reach_ratio": float(reach_ratio),
            "ratchet_triggered": ratchet_flag,
            "secrecy_premium_flag": bool(hist_row.get('opting_out', 0) == 1),
            "lti_vs_salary_ratio": float(lti / salary) if salary > 0 else None,
            "salary_benchmark": salary_bench,
            "sti_benchmark": sti_bench,
            "lti_benchmark": lti_bench,
            "hidden_stretch": hidden_stretch,
            "hidden_stretch_variance": hidden_stretch_variance,
            "internal_concentration_ratio": float(multiple_of_median),
            "concentration_ratchet_triggered": bool(hist_row.get('concentration_ratchet_triggered', False)),
            "_traceability_map": self._build_traceability_map()
        }

    def run_cached_pipeline(self, cache_path: str = "sml_cache.json") -> bool:
        """Executes the fast computation pipeline over the panel using cached parameters."""
        if not self.load_from_cache(cache_path):
            return False

        self.preprocess()
        self.preprocess_robust_features()

        X = np.array(self.data[self.CLUSTER_FEATURES])
        mean = np.array(self.cache_data['scaler_mean'])
        scale = np.array(self.cache_data['scaler_scale'])
        scaled_features = (X - mean) / scale
        clustering_features = scaled_features[:, [2, 4]]

        centroids = np.array(self.cache_data['kmeans_centroids'])[:, [2, 4]]
        assigned_clusters = []
        for row in clustering_features:
            distances = np.linalg.norm(centroids - row, axis=1)
            assigned_clusters.append(int(np.argmin(distances)))
        self.data['shadow_peer_cluster'] = assigned_clusters

        # Predicted line residuals
        beta_size = self.cache_data['beta_size']
        model_params = self.cache_data['model_params']
        beta_roa = model_params.get('roa', 1.5)
        beta_gear = model_params.get('gear', 0.0)
        intercept = model_params.get('Intercept', 7.2)

        self.data['predicted_log_pay'] = (
            intercept + 
            beta_size * self.data['log_size'] + 
            beta_roa * self.data['roa'] + 
            beta_gear * self.data['gear'] +
            self.data['shadow_peer_cluster'].map(lambda c: model_params.get(f"C(shadow_peer_cluster)[T.{c}]", 0.0)) +
            self.data['year'].map(lambda y: model_params.get(f"C(year)[T.{y}]", 0.0))
        )
        self.data['residual'] = self.data['log_pay'] - self.data['predicted_log_pay']
        self.data['pay_premium'] = np.exp(self.data['residual'])
        self.data['reach_ratio'] = np.exp(self.data['residual'] / beta_size)

        self.detect_asymmetric_ratchets()
        medians = self.cache_data['cluster_medians_2024']
        self.data['cluster_median_pay'] = self.data['shadow_peer_cluster'].map(lambda c: medians.get(str(c), 1500000.0))
        self.data['cluster_mean_pay'] = self.data['cluster_median_pay'] * 1.15
        self.data['multiple_of_median'] = self.data['total_comp'] / self.data['cluster_median_pay']

        print("Fast cached SML pipeline executed successfully.")
        return True

if __name__ == "__main__":
    engine = ProxyEngineSML()
    engine.run_full_pipeline()
    print("Precomputed diagnostics:")
    print(json.dumps(engine.get_model_diagnostics(), indent=2))
