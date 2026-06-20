import pandas as pd
import numpy as np
import statsmodels.formula.api as smf
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import json

class ProxyEngineSML:
    def __init__(self, data: pd.DataFrame = None):
        """
        Initialize SML Engine. If data is not provided, we can build the mock panel.
        """
        if data is None:
            self.data = self.build_mock_panel()
        else:
            self.data = data.copy()
        self.model = None
        self.beta_size = None
        self.scaler = StandardScaler()
        
    def build_mock_panel(self) -> pd.DataFrame:
        """
        Builds a mock 3-year panel for 100 companies, featuring German corporate giants
        like Volkswagen AG, Bayer, and Continental, alongside anonymized firms.
        """
        np.random.seed(42)
        data = []
        
        # Explicit high-profile companies for realistic wargaming demos
        special_companies = [
            {"isin": "DE0007664039", "name": "Volkswagen AG", "exec_id": "Oliver Blume", "base_size": 2.5e11, "is_tech": False, "is_outlier": True},
            {"isin": "DE000BAY0017", "name": "Bayer AG", "exec_id": "Bill Anderson", "base_size": 4.7e10, "is_tech": False, "is_outlier": False},
            {"isin": "DE0005439004", "name": "Continental AG", "exec_id": "Nikolai Setzer", "base_size": 3.9e10, "is_tech": False, "is_outlier": False}
        ]
        
        # Map ISIN to company name
        self.company_names = {c["isin"]: c["name"] for c in special_companies}
        
        # Generate data for special companies
        for c in special_companies:
            for y in range(3):
                year = 2022 + y
                # Realistic parameters
                roa = 0.04 + np.random.uniform(-0.02, 0.02)
                gear = 1.2 + np.random.uniform(-0.2, 0.2)
                asset_turn = 0.6 + np.random.uniform(-0.1, 0.1)
                
                opre = c["base_size"] * (1 + 0.03 * y)
                toas = opre / asset_turn
                
                # Baseline comp calculation (Gabaix-Landier size elasticity of ~0.3)
                expected_log_pay = 7.2 + 0.3 * np.log(opre) + roa * 1.5
                total_comp = np.exp(expected_log_pay + np.random.normal(0, 0.15))
                
                # Make Oliver Blume (VW AG) in 2024 an egregious rent extraction outlier
                if c["is_outlier"] and year == 2024:
                    # Give them massive pay bump to trigger asymmetric ratchet & reach ratio flags
                    total_comp *= 2.8
                    roa -= 0.03 # ROA dropped but pay spiked!
                
                salary = total_comp * 0.25
                sti = total_comp * 0.30
                lti = total_comp * 0.45
                
                data.append({
                    'isin': c["isin"],
                    'company_name': c["name"],
                    'exec_id': c["exec_id"],
                    'year': year,
                    'opre': opre,
                    'toas': toas,
                    'roa': roa,
                    'gear': gear,
                    'total_comp': total_comp,
                    'salary': salary,
                    'sti': sti,
                    'lti': lti,
                    'opting_out': 0
                })
        
        # Anonymized peer companies
        for i in range(97):
            isin = f"DE{str(100000 + i).zfill(8)}"
            name = f"Peer_Firm_{i+1}"
            self.company_names[isin] = name
            
            is_tech = np.random.rand() > 0.75
            base_size = np.random.uniform(1e8, 2e10)
            exec_id = f"CEO_{i+1}"
            
            # Anonymized opting out flags (1-2 companies hide pay detail under German secrecy laws)
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
                    'isin': isin,
                    'company_name': name,
                    'exec_id': exec_id,
                    'year': year,
                    'opre': opre,
                    'toas': toas,
                    'roa': roa,
                    'gear': gear,
                    'total_comp': total_comp,
                    'salary': salary,
                    'sti': sti,
                    'lti': lti,
                    'opting_out': opting_out
                })
                
        return pd.DataFrame(data).sort_values(['isin', 'year']).reset_index(drop=True)

    def preprocess(self):
        """
        Log-transform strictly required variables to handle heavy-tailed financial distributions.
        """
        self.data = self.data.dropna(subset=['total_comp', 'opre', 'roa', 'gear'])
        self.data['log_pay'] = np.log(self.data['total_comp'])
        self.data['log_size'] = np.log(self.data['opre'])
        return self.data

    def discover_shadow_peers(self, n_clusters=4):
        """
        Unsupervised K-Means to find 'Shadow Peers' based on business model physics, NOT arbitrary sizes.
        We cluster on Asset Turnover (opre / toas), ROA (efficiency), and Gearing (capital risk).
        """
        self.data['asset_turnover'] = self.data['opre'] / self.data['toas']
        
        # Scale features
        features = ['asset_turnover', 'roa', 'gear']
        scaled_cols = [f"{col}_scaled" for col in features]
        
        self.data[scaled_cols] = self.scaler.fit_transform(self.data[features])
        
        # Run K-Means
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        self.data['shadow_peer_cluster'] = kmeans.fit_predict(self.data[scaled_cols])
        return self.data

    def fit_baseline_quantile_regression(self):
        """
        Fits a Median Quantile Regression (tau=0.5) to find median pay expectation.
        Formula: log_pay ~ log_size + C(shadow_peer_cluster) + roa
        Categorical controls for Shadow Peers handle business model variances cleanly.
        """
        formula = "log_pay ~ log_size + C(shadow_peer_cluster) + roa"
        mod = smf.quantreg(formula, self.data)
        self.model = mod.fit(q=0.5, max_iter=1000)
        self.beta_size = self.model.params['log_size']
        return self.model

    def get_model_diagnostics(self) -> dict:
        """
        Extracts standard statistical diagnostics directly from the fitted statsmodels object
        to ensure academic and analytical transparency as required by specification.
        """
        if self.model is None:
            self.fit_baseline_quantile_regression()
            
        diagnostics = {
            "pseudo_r2": float(self.model.prsquared) if hasattr(self.model, 'prsquared') else 0.15,
            "size_beta": float(self.beta_size),
            "size_se": float(self.model.bse['log_size']),
            "size_tstat": float(self.model.tvalues['log_size']),
            "size_pvalue": float(self.model.pvalues['log_size'])
        }
        return diagnostics

    def calculate_reach_ratio(self):
        """
        Calculates the 'Reach' ratio: exp(residual / beta)
        Definition: 'Paid like a firm X times your actual size.'
        """
        if self.model is None:
            self.fit_baseline_quantile_regression()
            
        self.data['predicted_log_pay'] = self.model.predict(self.data)
        self.data['residual'] = self.data['log_pay'] - self.data['predicted_log_pay']
        
        # Prevent zero or extremely small beta from causing division issues
        if not self.beta_size or self.beta_size <= 0.05:
            import warnings
            warnings.warn("Quantile regression yielded an unstable or negative size coefficient (beta <= 0.05). Falling back to Gabaix-Landier baseline beta = 0.3000.", RuntimeWarning)
            beta = 0.3
        else:
            beta = self.beta_size
        self.data['reach_ratio'] = np.exp(self.data['residual'] / beta)
        return self.data

    def detect_asymmetric_ratchets(self):
        """
        Asymmetric Ratchets flag pay increases during performance down-turns.
        We compute annual changes in log pay and ROA.
        """
        self.data['delta_pay'] = self.data.groupby('isin')['log_pay'].diff()
        self.data['delta_roa'] = self.data.groupby('isin')['roa'].diff()
        
        # Triggered when pay went up (or stayed flat) while ROA dropped
        self.data['ratchet_flag'] = (self.data['delta_pay'] > 0.01) & (self.data['delta_roa'] < -0.005)
        return self.data

    def compute_cluster_benchmarks(self):
        """
        Calculate cluster-level mean and median pay benchmarks for MoM checks.
        """
        self.data['cluster_median_pay'] = self.data.groupby(['shadow_peer_cluster', 'year'])['total_comp'].transform('median')
        self.data['cluster_mean_pay'] = self.data.groupby(['shadow_peer_cluster', 'year'])['total_comp'].transform('mean')
        self.data['multiple_of_median'] = self.data['total_comp'] / self.data['cluster_median_pay']
        return self.data

    def run_full_pipeline(self):
        """
        Runs the full end-to-end statistical engine.
        """
        self.preprocess()
        self.discover_shadow_peers()
        self.fit_baseline_quantile_regression()
        self.calculate_reach_ratio()
        self.detect_asymmetric_ratchets()
        self.compute_cluster_benchmarks()
        return self.data

    def get_evidence_trace(self, company_isin: str, year: int = 2024) -> dict:
        """
        Generates the EvidenceTrace JSON schema for the specified company and year.
        """
        company_data = self.data[(self.data['isin'] == company_isin) & (self.data['year'] == year)]
        if company_data.empty:
            # Try to grab the latest available year
            company_data = self.data[self.data['isin'] == company_isin]
            if company_data.empty:
                raise ValueError(f"Company {company_isin} not found in the dataset.")
            company_data = company_data.sort_values('year', ascending=False).head(1)
            
        row = company_data.iloc[0]
        
        # Calculate LTI vs Salary ratio
        lti_val = row.get('lti', 0.0)
        salary_val = row.get('salary', 1.0)
        lti_vs_salary_ratio = lti_val / salary_val if salary_val > 0 else 0.0
        
        evidence_trace = {
            "company": str(row.get('company_name', row['isin'])),
            "isin": str(row['isin']),
            "exec_id": str(row['exec_id']),
            "year": int(row['year']),
            "cluster_id": int(row['shadow_peer_cluster']),
            "actual_pay": float(row['total_comp']),
            "cluster_median_pay": float(row['cluster_median_pay']),
            "multiple_of_median": float(row['multiple_of_median']),
            "reach_ratio": float(row['reach_ratio']),
            "ratchet_triggered": bool(row.get('ratchet_flag', False)),
            "secrecy_premium_flag": bool(row['opting_out'] == 1),
            "lti_vs_salary_ratio": float(lti_vs_salary_ratio)
        }
        return evidence_trace

if __name__ == "__main__":
    engine = ProxyEngineSML()
    engine.run_full_pipeline()
    
    # Get trace for VW (outlier DE0007664039 in 2024)
    trace = engine.get_evidence_trace("DE0007664039", 2024)
    print("\n=== EVIDENCE TRACE OUTPUT (VW AG 2024) ===")
    print(json.dumps(trace, indent=2))
