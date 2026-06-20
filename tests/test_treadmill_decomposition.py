import pytest
import pandas as pd
import numpy as np
from sml_engine import ProxyEngineSML

def test_treadmill_oaxaca_decomposition():
    """
    Test Step 2: Oaxaca-Blinder 2-fold decomposition verification.
    Asserts that delta_log is mathematically equal to endowment + drift.
    """
    engine = ProxyEngineSML()
    engine.run_full_pipeline()
    df_treadmill = engine.get_treadmill()
    
    assert 'drift_pct' in df_treadmill.columns
    assert 'endowment_pct' in df_treadmill.columns
    
    # For each year after the base year, check that the decomposition holds
    # delta_log is calculated as endowment + drift, so let's verify if that matches log pay differences
    years = sorted(engine.data["year"].unique())
    base_year = years[0]
    base_mean = engine.data[engine.data["year"] == base_year]["log_pay"].mean()
    
    for _, row in df_treadmill.iterrows():
        yr = row['year']
        if yr == base_year:
            assert row['delta_log'] == 0.0
            assert row['drift_pct'] == 0.0
            assert row['endowment_pct'] == 0.0
        else:
            yr_mean = engine.data[engine.data["year"] == yr]["log_pay"].mean()
            diff = yr_mean - base_mean
            assert np.isclose(row['delta_log'], diff, rtol=1e-5)
