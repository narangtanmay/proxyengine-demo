import pandas as pd
import numpy as np
import statsmodels.formula.api as smf
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import warnings
warnings.filterwarnings('ignore')

def generate_robust_mock_data(n_firms=100, years=5):
    np.random.seed(42)
    data = []
    for i in range(n_firms):
        isin = f"DE{str(i).zfill(10)}"
        is_tech = np.random.rand() > 0.7
        base_size = np.random.uniform(1e7, 1e10)
        
        for y in range(years):
            year = 2019 + y
            size_y = base_size * (1 + 0.05 * y + np.random.normal(0, 0.02))
            
            if is_tech:
                roa = np.random.uniform(0.08, 0.20)
                gear = np.random.uniform(0.1, 0.6)
                asset_turn = np.random.uniform(1.5, 3.0)
            else:
                roa = np.random.uniform(0.01, 0.07)
                gear = np.random.uniform(0.8, 2.5)
                asset_turn = np.random.uniform(0.4, 1.2)
                
            opre = size_y
            toas = opre / asset_turn
            
            # THE TRUE DATA GENERATING PROCESS (DGP)
            # This simulates reality where pay is intrinsically linked to size elasticity (~0.3)
            expected_log_pay = 10 + 0.3 * np.log(opre) + roa * 2
            
            # The actual pay the CEO receives (includes random noise/luck/overpayment)
            actual_total_comp = np.exp(expected_log_pay + np.random.normal(0, 0.2))
            
            data.append({
                'isin': isin, 'year': year, 'exec_id': f'CEO_{isin}',
                'opre': opre, 'toas': toas,
                'roa': roa, 'gear': gear, 'actual_total_comp': actual_total_comp
            })
            
    df = pd.DataFrame(data)
    df['log_actual_pay'] = np.log(df['actual_total_comp'])
    df['log_size'] = np.log(df['opre'])
    return df

def run_proof():
    df = generate_robust_mock_data()
    
    # 1. Cluster using Asset Turnover, ROA, GEAR
    df['asset_turnover'] = df['opre'] / df['toas']
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(df[['asset_turnover', 'roa', 'gear']])
    kmeans = KMeans(n_clusters=4, random_state=42, n_init=10)
    df['shadow_peer_cluster'] = kmeans.fit_predict(scaled_features)
    
    # 2. THE CORRECT REGRESSION (Y = Actual Individual Pay)
    print("=== THE CORRECT REGRESSION (Y = Actual Pay) ===")
    print("Formula: log_actual_pay ~ log_size + C(shadow_peer_cluster) + roa")
    
    mod_correct = smf.quantreg("log_actual_pay ~ log_size + C(shadow_peer_cluster) + roa", df).fit(q=0.5)
    print(f"Recovered Beta (Size Elasticity): {mod_correct.params['log_size']:.4f}")
    
    print("\n--------------------------------------------------\n")
    
    # 3. THE USER'S HYPOTHESIS (Y = Median Cluster Pay)
    df['median_cluster_pay'] = df.groupby('shadow_peer_cluster')['actual_total_comp'].transform('median')
    df['log_median_cluster_pay'] = np.log(df['median_cluster_pay'])

    print("=== THE USER'S HYPOTHESIS (Y = Median Cluster Pay) ===")
    print("Formula: log_median_cluster_pay ~ log_size + C(shadow_peer_cluster) + roa")
    try:
        mod_user = smf.quantreg("log_median_cluster_pay ~ log_size + C(shadow_peer_cluster) + roa", df).fit(q=0.5)
        print(f"Recovered Beta (Size Elasticity): {mod_user.params['log_size']:.4f}")
    except Exception as e:
        print(f"Regression Failed: {e}")

if __name__ == "__main__":
    run_proof()
