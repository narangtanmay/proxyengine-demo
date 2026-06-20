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
        # Business model archetype
        is_tech = np.random.rand() > 0.7
        base_size = np.random.uniform(1e7, 1e10)
        
        for y in range(years):
            year = 2019 + y
            # Add growth
            size_y = base_size * (1 + 0.05 * y + np.random.normal(0, 0.02))
            
            if is_tech:
                roa = np.random.uniform(0.08, 0.20)
                gear = np.random.uniform(0.1, 0.6)
                asset_turn = np.random.uniform(1.5, 3.0)
                rev_per_emp = np.random.uniform(500000, 1500000)
            else:
                roa = np.random.uniform(0.01, 0.07)
                gear = np.random.uniform(0.8, 2.5)
                asset_turn = np.random.uniform(0.4, 1.2)
                rev_per_emp = np.random.uniform(100000, 400000)
                
            opre = size_y
            toas = opre / asset_turn
            empl = opre / rev_per_emp
            pl = toas * roa
            
            # Pay generation: log(Pay) = alpha + 0.3 * log(Size) + roa + error
            expected_log_pay = 10 + 0.3 * np.log(opre) + roa * 2
            total_comp = np.exp(expected_log_pay + np.random.normal(0, 0.2))
            
            data.append({
                'isin': isin, 'year': year, 'exec_id': f'CEO_{isin}',
                'opre': opre, 'toas': toas, 'empl': empl, 'pl': pl,
                'roa': roa, 'gear': gear, 'total_comp': total_comp
            })
            
    df = pd.DataFrame(data)
    df['log_pay'] = np.log(df['total_comp'])
    df['log_size'] = np.log(df['opre'])
    df['yearly_median_opre'] = df.groupby('year')['opre'].transform('median')
    df['turnover_per_median'] = np.log(df['opre'] / df['yearly_median_opre'])
    return df

def test_clustering_approaches():
    df = generate_robust_mock_data()
    print(f"Dataset generated: {len(df)} firm-years\n")
    
    # --- APPROACH A: The "Kitchen Sink" (User's suggested list) ---
    print("=== APPROACH A: Clustering on TOAS, Turnover/Median, EMPL, PL, OPRE, ROA, GEAR ===")
    features_A = ['toas', 'turnover_per_median', 'empl', 'pl', 'opre', 'roa', 'gear']
    scaler_A = StandardScaler()
    scaled_A = scaler_A.fit_transform(df[features_A])
    
    kmeans_A = KMeans(n_clusters=4, random_state=42, n_init=10)
    df['cluster_A'] = kmeans_A.fit_predict(scaled_A)
    
    try:
        mod_A = smf.quantreg("log_pay ~ log_size + C(cluster_A) + roa + gear", df).fit(q=0.5)
        print(f"Approach A - Size Elasticity (Beta): {mod_A.params['log_size']:.4f}")
        print(f"Approach A - Standard Error for Size: {mod_A.bse['log_size']:.4f}")
    except Exception as e:
        print(f"Approach A Failed: {e}")

    # --- APPROACH B: The "Economic Physics" (My Recommendation) ---
    print("\n=== APPROACH B: Clustering on Asset Turnover (OPRE/TOAS), ROA, GEAR ===")
    df['asset_turnover'] = df['opre'] / df['toas']
    features_B = ['asset_turnover', 'roa', 'gear']
    scaler_B = StandardScaler()
    scaled_B = scaler_B.fit_transform(df[features_B])
    
    kmeans_B = KMeans(n_clusters=4, random_state=42, n_init=10)
    df['cluster_B'] = kmeans_B.fit_predict(scaled_B)
    
    try:
        mod_B = smf.quantreg("log_pay ~ log_size + C(cluster_B) + roa + gear", df).fit(q=0.5)
        print(f"Approach B - Size Elasticity (Beta): {mod_B.params['log_size']:.4f}")
        print(f"Approach B - Standard Error for Size: {mod_B.bse['log_size']:.4f}")
    except Exception as e:
        print(f"Approach B Failed: {e}")
        
    print("\n--- Why does this happen? ---")
    print(f"Variance of log_size WITHIN Cluster 0 (Approach A): {df[df['cluster_A']==0]['log_size'].var():.4f}")
    print(f"Variance of log_size WITHIN Cluster 0 (Approach B): {df[df['cluster_B']==0]['log_size'].var():.4f}")

if __name__ == "__main__":
    test_clustering_approaches()
