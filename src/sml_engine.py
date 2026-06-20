import pandas as pd
import numpy as np
import statsmodels.formula.api as smf
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

class ProxyEngineSML:
    def __init__(self, data: pd.DataFrame):
        """
        Initialize the SML Engine with the joined ORBIS + Board Pay panel.
        Expected columns: 'isin', 'exec_id', 'year', 'total_comp', 'opre', 'roa', 'gear'
        """
        self.data = data.copy()
        self.model = None
        self.beta_size = None
        
    def preprocess(self):
        """
        Log-transform strictly required variables to handle heavy-tailed financial distributions.
        """
        self.data = self.data.dropna(subset=['total_comp', 'opre', 'roa', 'gear'])
        self.data['log_pay'] = np.log(self.data['total_comp'] + 1)
        self.data['log_size'] = np.log(self.data['opre'] + 1)
        print(f"Data preprocessed. Clean rows available: {len(self.data)}")
        return self.data

    def discover_shadow_peers(self, n_clusters=3):
        """
        Unsupervised K-Means to find 'Shadow Peers' based on business model, NOT size.
        We cluster on ROA (efficiency) and Gear (Risk/Capital Structure).
        This isolates asset-heavy industrials from asset-light tech.
        """
        print(f"Running K-Means (k={n_clusters}) to group Shadow Peers...")
        features = self.data[['roa', 'gear']]
        scaler = StandardScaler()
        scaled_features = scaler.fit_transform(features)
        
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        self.data['shadow_peer_cluster'] = kmeans.fit_predict(scaled_features)
        print("Shadow Peer clusters assigned.")
        return self.data

    def fit_baseline_quantile_regression(self):
        """
        Fits a Median Quantile Regression (tau=0.5).
        Formula: log_pay ~ log_size + C(shadow_peer_cluster) + roa + gear
        By including the cluster as a categorical fixed effect, we control for the business model.
        """
        print("Fitting Quantile Regression (tau=0.5)...")
        # Formula includes the shadow peer cluster as a categorical control
        formula = "log_pay ~ log_size + C(shadow_peer_cluster) + roa + gear"
        
        mod = smf.quantreg(formula, self.data)
        self.model = mod.fit(q=0.5, max_iter=1000)
        
        self.beta_size = self.model.params['log_size']
        print(f"Model Fit Complete. Size Elasticity (beta) = {self.beta_size:.4f}")
        
        if not (0.1 < self.beta_size < 0.5):
            print("WARNING: Beta is outside the standard 0.1 - 0.5 range. Check data join!")
            
        return self.model

    def calculate_reach_ratio(self):
        """
        Calculates the 'Reach' ratio: exp(residual / beta)
        Definition: 'Paid like a firm X times your actual size.'
        """
        if self.model is None:
            raise ValueError("Must fit the baseline model before calculating Reach.")
            
        self.data['predicted_log_pay'] = self.model.predict(self.data)
        self.data['residual'] = self.data['log_pay'] - self.data['predicted_log_pay']
        
        beta = self.beta_size if self.beta_size > 0 else 0.3 # Fallback
        self.data['reach_ratio'] = np.exp(self.data['residual'] / beta)
        
        print("Reach Ratios calculated successfully.")
        return self.data[['isin', 'year', 'exec_id', 'shadow_peer_cluster', 'total_comp', 'residual', 'reach_ratio']]

if __name__ == "__main__":
    # Generate mock DAX40 data (Expanded to 10 rows to allow K-Means and Quantile to run without singular matrix errors)
    np.random.seed(42)
    mock_data = pd.DataFrame({
        'isin': [f'DE000000000{i}' for i in range(10)],
        'exec_id': [f'E{i}' for i in range(10)],
        'year': [2023] * 10,
        'total_comp': [3000000, 5000000, 15000000, 2000000, 4000000, 3500000, 6000000, 2500000, 12000000, 1800000],
        'opre': [1e7, 5e7, 1.2e7, 8e6, 3e7, 2e7, 6e7, 9e6, 1.5e7, 7e6], 
        'roa': [0.05, 0.08, 0.02, 0.04, 0.06, 0.07, 0.09, 0.03, 0.01, 0.05],
        'gear': [1.2, 0.8, 1.5, 1.0, 1.1, 0.9, 0.7, 1.4, 1.6, 1.0]
    })
    
    engine = ProxyEngineSML(mock_data)
    engine.preprocess()
    engine.discover_shadow_peers(n_clusters=2) # 2 clusters for this tiny mock dataset
    engine.fit_baseline_quantile_regression()
    results = engine.calculate_reach_ratio()
    
    print("\n--- EVIDENCE TRACE OUTPUT (JSON Ready) ---")
    print(results.to_json(orient='records', indent=2))