import pandas as pd
import numpy as np
import statsmodels.formula.api as smf
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import json
import warnings
warnings.filterwarnings('ignore')

def build_mock_panel():
    """Builds a mock 3-year panel for 100 companies."""
    np.random.seed(42)
    data = []
    for i in range(100):
        isin = f"DE{str(i).zfill(6)}"
        is_tech = np.random.rand() > 0.7
        base_size = np.random.uniform(1e7, 1e10)
        
        for y in range(3):
            year = 2021 + y
            roa = np.random.uniform(0.01, 0.20)
            gear = np.random.uniform(0.1, 2.5)
            asset_turn = np.random.uniform(0.5, 3.0) if is_tech else np.random.uniform(0.2, 1.0)
            
            opre = base_size * (1 + 0.05 * y)
            toas = opre / asset_turn
            
            expected_log_pay = 10 + 0.3 * np.log(opre) + roa * 2
            total_comp = np.exp(expected_log_pay + np.random.normal(0, 0.2))
            
            # Make one specific company an egregious outlier for the demo
            if isin == "DE000001" and year == 2023:
                total_comp *= 4.0  # 4x overpaid outlier ("Shoot out point")
                
            data.append({
                'isin': isin, 'exec_id': f'CEO_{isin}', 'year': year,
                'opre': opre, 'toas': toas, 'roa': roa, 'gear': gear,
                'total_comp': total_comp,
                'salary': total_comp * 0.3,
                'multi_year_bonus_grants': total_comp * 0.5,
                'opting_out': 1 if isin == 'DE000001' else 0
            })
    return pd.DataFrame(data).sort_values(['isin', 'year'])

def run_pipeline():
    df = build_mock_panel()
    print(f"1. Data Ingested: {len(df)} rows.")

    df['log_pay'] = np.log(df['total_comp'])
    df['log_size'] = np.log(df['opre'])

    # --- ML LAYER: CLUSTERING SHADOW PEERS ---
    print("\n2. ML Layer: Clustering Shadow Peers...")
    df['asset_turnover'] = df['opre'] / df['toas']
    scaler = StandardScaler()
    df[['asset_turn_scaled', 'roa_scaled', 'gear_scaled']] = scaler.fit_transform(df[['asset_turnover', 'roa', 'gear']])
    
    kmeans = KMeans(n_clusters=5, random_state=42, n_init=10)
    df['shadow_peer_cluster'] = kmeans.fit_predict(df[['asset_turn_scaled', 'roa_scaled', 'gear_scaled']])

    # --- THE USER'S IDEA: CLUSTER MEAN/MEDIAN BENCHMARKING ---
    print("\n3. SML Layer A: Cluster-Level Outlier Smoothing (Multiple of Median/Mean)...")
    # By taking the median of the cluster, we smooth out individual "shoot out points" (outliers)
    df['cluster_median_pay'] = df.groupby(['shadow_peer_cluster', 'year'])['total_comp'].transform('median')
    df['cluster_mean_pay'] = df.groupby(['shadow_peer_cluster', 'year'])['total_comp'].transform('mean')
    
    # ISS Multiple of Median (MoM) metric
    df['multiple_of_median'] = df['total_comp'] / df['cluster_median_pay']

    # --- SML LAYER B: QUANTILE REGRESSION (Continuous Size Adjustment) ---
    print("4. SML Layer B: Quantile Regression & Reach Ratio...")
    # Using Median Quantile Regression (q=0.5) ALSO ignores "shoot out points" mathematically
    formula = "log_pay ~ log_size + C(shadow_peer_cluster) + roa"
    model = smf.quantreg(formula, df).fit(q=0.5)
    beta_size = model.params['log_size']
    
    df['expected_log_pay'] = model.predict(df)
    df['residual'] = df['log_pay'] - df['expected_log_pay']
    fallback_beta = beta_size if beta_size > 0.1 else 0.3
    df['reach_ratio'] = np.exp(df['residual'] / fallback_beta)

    # --- SML LAYER C: ASYMMETRIC RATCHETS ---
    print("5. SML Layer C: Asymmetric Ratchet Detection...")
    df['delta_pay'] = df.groupby('isin')['log_pay'].diff()
    df['delta_roa'] = df.groupby('isin')['roa'].diff()
    df['ratchet_flag'] = (df['delta_pay'] >= 0) & (df['delta_roa'] < 0)

    # --- EVIDENCE TRACE EXPORT ---
    print("\n=== EVIDENCE TRACE OUTPUT (Outlier DE000001) ===")
    outlier = df[(df['isin'] == 'DE000001') & (df['year'] == 2023)].iloc[0]
    
    evidence_trace = {
        "company": outlier['isin'],
        "cluster_id": int(outlier['shadow_peer_cluster']),
        "actual_pay": round(outlier['total_comp'], 2),
        "cluster_median_pay": round(outlier['cluster_median_pay'], 2),
        "multiple_of_median": round(outlier['multiple_of_median'], 2), # The user's requested logic
        "reach_ratio": round(outlier['reach_ratio'], 2),               # Mikhail's logic
        "ratchet_triggered": bool(outlier['ratchet_flag']),
        "secrecy_premium_flag": bool(outlier['opting_out'] == 1)
    }
    
    print(json.dumps(evidence_trace, indent=2))

if __name__ == "__main__":
    run_pipeline()
