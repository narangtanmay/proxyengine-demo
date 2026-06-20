import sys
import os
import pandas as pd
import numpy as np
import pytest

# Ensure local src directory is in path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src"))

from sml_engine import ProxyEngineSML

def generate_background_market_data() -> pd.DataFrame:
    """Helper to generate background peer market panel data."""
    # Leverage the standard mock panel built by ProxyEngineSML directly to maintain code consistency
    engine = ProxyEngineSML()
    return engine.data.copy()

def test_allianz_2025_lti_structural_imbalance():
    """
    Benchmark Test 4: Allianz SE (2025)
    Ground Truth: ISS recommended AGAINST the Remuneration Policy (Agenda Item 7).
    Reason: Excessive LTI multiplier compared to fixed base salary (breaching DCGK G.1).
    Validation: SML engine must flag the LTI-to-salary ratio when it exceeds the 4.0x imbalance threshold.
    """
    df_market = generate_background_market_data()
    
    # Inject Allianz 2025 profile with extremely high LTI vs fixed base
    allianz_data = pd.DataFrame([{
        'isin': 'DE0008404005',
        'company_name': 'Allianz SE',
        'exec_id': 'CEO_ALV',
        'year': 2025,
        'opre': 1.6e11,  # Scale: 160B
        'toas': 1.1e12,
        'roa': 0.08,
        'gear': 0.9,
        'total_comp': 12000000.0,
        'salary': 1800000.0,      # Fixed Base
        'sti': 2200000.0,         # Short-Term Variable
        'lti': 8000000.0,         # LTI is 4.4x salary!
        'opting_out': 0
    }])
    
    df_combined = pd.concat([df_market, allianz_data], ignore_index=True)
    engine = ProxyEngineSML(df_combined)
    engine.run_full_pipeline()
    
    trace = engine.get_evidence_trace('DE0008404005', 2025)
    
    # Assert high LTI ratio is successfully captured and exposed
    assert trace['lti_vs_salary_ratio'] > 4.0, f"Failed to catch Allianz's G.1 structural imbalance! Ratio was {trace['lti_vs_salary_ratio']}"

def test_dhl_2024_pay_performance_disconnect():
    """
    Benchmark Test 5: DHL Group (2024)
    Ground Truth: Strong shareholder pushback on the remuneration report under Agenda Item 7.
    Reason: High STV bonus payout despite operational ROA contraction.
    Validation: Panel regression must flag the disconnect between variable bonus changes and asset efficiency changes.
    """
    df_market = generate_background_market_data()
    
    # Inject DHL 2023-2024 profile showing STV payout escalation despite ROA drop
    dhl_data = pd.DataFrame([
        {
            'isin': 'DE0005552004',
            'company_name': 'DHL Group',
            'exec_id': 'CEO_DHL',
            'year': 2023,
            'opre': 8.1e10,
            'toas': 6.0e10,
            'roa': 0.07,
            'gear': 1.1,
            'total_comp': 5500000.0,
            'salary': 1500000.0,
            'sti': 1500000.0,
            'lti': 2500000.0,
            'opting_out': 0
        },
        {
            'isin': 'DE0005552004',
            'company_name': 'DHL Group',
            'exec_id': 'CEO_DHL',
            'year': 2024,
            'opre': 8.2e10,
            'toas': 6.1e10,
            'roa': 0.04,               # Asset efficiency contracts significantly
            'gear': 1.1,
            'total_comp': 6000000.0,  # Total compensation goes UP
            'salary': 1500000.0,
            'sti': 2000000.0,          # STV went up despite performance contraction!
            'lti': 2500000.0,
            'opting_out': 0
        }
    ])
    
    df_combined = pd.concat([df_market, dhl_data], ignore_index=True)
    engine = ProxyEngineSML(df_combined)
    engine.run_full_pipeline()
    
    trace = engine.get_evidence_trace('DE0005552004', 2024)
    
    # Assert model successfully flags the lack of downside risk alignment
    assert trace['ratchet_triggered'] is True, "Model failed to catch DHL's pay-for-performance disconnect!"
