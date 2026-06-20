import pandas as pd
import numpy as np
import pytest
import sys
import os

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), '../src'))
from sml_engine import ProxyEngineSML

def generate_background_market_data():
    """Generates a stable background market so the regressions have enough degrees of freedom to fit."""
    np.random.seed(42)
    data = []
    for i in range(50):
        isin = f"DE{str(i).zfill(6)}"
        base_size = np.random.uniform(1e7, 1e9)
        for year in [2019, 2020, 2021, 2022]:
            roa = np.random.uniform(0.02, 0.15)
            gear = np.random.uniform(0.5, 1.5)
            asset_turn = np.random.uniform(0.5, 2.0)
            opre = base_size * (1 + 0.03 * (year - 2019))
            toas = opre / asset_turn
            
            # Normal pay scaling
            expected_log_pay = 10 + 0.3 * np.log(opre) + roa * 2
            total_comp = np.exp(expected_log_pay + np.random.normal(0, 0.1))
            
            data.append({
                'isin': isin, 'exec_id': f'CEO_{isin}', 'year': year,
                'opre': opre, 'toas': toas, 'roa': roa, 'gear': gear,
                'total_comp': total_comp, 'salary': total_comp * 0.3,
                'multi_year_bonus_grants': total_comp * 0.5, 'opting_out': 0
            })
    return pd.DataFrame(data)

def test_bayer_2020_asymmetric_ratchet():
    """
    Benchmark Test 1: Bayer AG (2020)
    Ground Truth: Shareholders rejected the pay package (20% approval).
    Reason: Executives were paid huge bonuses while ROA/TSR crashed due to Monsanto fallout.
    Validation: Model MUST trigger 'ratchet_triggered' = True (pay went up/flat while ROA dropped).
    """
    df_market = generate_background_market_data()
    
    # Inject Bayer 2019-2020 profile
    bayer_data = pd.DataFrame({
        'isin': ['DE000BAY0017', 'DE000BAY0017'],
        'exec_id': ['CEO_BAY', 'CEO_BAY'],
        'year': [2019, 2020],
        'opre': [43000000, 41000000],      # Size drops slightly
        'toas': [120000000, 115000000],
        'roa': [0.06, 0.01],               # ROA CRASHES (Monsanto impact)
        'gear': [1.2, 1.3],
        'total_comp': [6000000, 6500000],  # Pay goes UP despite crash
        'salary': [1500000, 1500000],
        'multi_year_bonus_grants': [3000000, 3500000],
        'opting_out': [0, 0]
    })
    
    df_combined = pd.concat([df_market, bayer_data], ignore_index=True)
    engine = ProxyEngineSML(df_combined)
    engine.run_full_pipeline()
    
    trace = engine.get_evidence_trace('DE000BAY0017', 2020)
    
    # Assert the mathematical anomaly detector caught the historical scandal
    assert trace['ratchet_triggered'] is True, "Model failed to detect Bayer's 2020 Asymmetric Ratchet!"

def test_software_ag_2022_reach_anomaly():
    """
    Benchmark Test 2: Software AG (2022)
    Ground Truth: Shareholders rejected the pay package.
    Reason: Outsized pay packages compared to their MDAX/TecDAX size constraints.
    Validation: Model MUST trigger a high Reach Ratio (e.g., > 2.0)
    """
    df_market = generate_background_market_data()
    
    # Inject Software AG 2022 profile
    sag_data = pd.DataFrame({
        'isin': ['DE000A2GS401'],
        'exec_id': ['CEO_SAG'],
        'year': [2022],
        'opre': [850000],                  # Relatively small operating revenue
        'toas': [1000000],
        'roa': [0.08],
        'gear': [0.5],
        'total_comp': [8000000],           # Massive 8M compensation for a small firm
        'salary': [1000000],
        'multi_year_bonus_grants': [5000000],
        'opting_out': [0]
    })
    
    df_combined = pd.concat([df_market, sag_data], ignore_index=True)
    engine = ProxyEngineSML(df_combined)
    engine.run_full_pipeline()
    
    trace = engine.get_evidence_trace('DE000A2GS401', 2022)
    
    # Assert the mathematical anomaly detector caught the size/pay disconnect
    assert trace['reach_ratio'] > 2.0, f"Model failed to detect Software AG's Reach anomaly! Reach was {trace['reach_ratio']}"

def test_secrecy_premium_flag():
    """
    Benchmark Test 3: Opting Out Transparency
    Validation: Model MUST pass the opting_out flag through the evidence trace to trigger the DCGK warning.
    """
    df_market = generate_background_market_data()
    
    secret_firm = pd.DataFrame({
        'isin': ['DE000SECRET1'],
        'exec_id': ['CEO_SEC'],
        'year': [2022],
        'opre': [5000000],
        'toas': [6000000],
        'roa': [0.05],
        'gear': [1.0],
        'total_comp': [3000000],
        'salary': [1000000],
        'multi_year_bonus_grants': [1000000],
        'opting_out': [1]                  # Firm opted out of individual disclosure
    })
    
    df_combined = pd.concat([df_market, secret_firm], ignore_index=True)
    engine = ProxyEngineSML(df_combined)
    engine.run_full_pipeline()
    
    trace = engine.get_evidence_trace('DE000SECRET1', 2022)
    
    assert trace['secrecy_premium_flag'] is True, "Model failed to pass the transparency (opting_out) flag!"

if __name__ == "__main__":
    pytest.main(["-v", __file__])
