import pytest
import numpy as np
from sml_engine import ProxyEngineSML

def test_sml_stateless_parity():
    """
    Test Step 5: Stateless evaluation parity verification.
    Asserts that get_evidence_trace and evaluate_proposal_statelessly produce identical reach ratios.
    """
    engine = ProxyEngineSML()
    # Fit and save to cache to ensure cache is aligned
    engine.run_full_pipeline()
    engine.save_to_cache("sml_cache.json")
    
    # Reload engine to use the cache
    engine_cached = ProxyEngineSML()
    assert engine_cached.run_cached_pipeline("sml_cache.json")
    
    # Let's test a real company - Volkswagen AG
    company_isin = "DE0007664005"
    company_data = engine_cached.data[engine_cached.data['isin'] == company_isin]
    assert not company_data.empty, "Volkswagen AG not found in dataset"
    
    latest_year = int(company_data['year'].max())
    trace_stateful = engine_cached.get_evidence_trace(company_isin, latest_year)
    
    # Convert trace to proposal format
    proposal = {
        "company_name": "Volkswagen AG",
        "exec_id": trace_stateful["exec_id"],
        "proposed_salary": trace_stateful["salary_benchmark"], 
        "proposed_sti": trace_stateful["sti_benchmark"],
        "proposed_lti": trace_stateful["lti_benchmark"],
        "year": latest_year
    }
    
    row = company_data[company_data['year'] == latest_year].iloc[0]
    
    # Distribute total_comp proportionally to match components but sum up exactly to total_comp
    sum_components = float(row["salary"] + row["sti"] + row["lti"])
    if sum_components > 0:
        proposal["proposed_salary"] = float(row["salary"]) / sum_components * float(row["total_comp"])
        proposal["proposed_sti"] = float(row["sti"]) / sum_components * float(row["total_comp"])
        proposal["proposed_lti"] = float(row["lti"]) / sum_components * float(row["total_comp"])
    else:
        proposal["proposed_salary"] = float(row["total_comp"]) * 0.30
        proposal["proposed_sti"] = float(row["total_comp"]) * 0.35
        proposal["proposed_lti"] = float(row["total_comp"]) * 0.35
        
    trace_stateless = engine_cached.evaluate_proposal_statelessly(proposal)
    
    # Assert reach_ratio and other parameters match closely
    assert np.isclose(trace_stateful["reach_ratio"], trace_stateless["reach_ratio"], rtol=1e-4)
    assert np.isclose(trace_stateful["actual_pay"], trace_stateless["actual_pay"], rtol=1e-4)
    assert np.isclose(trace_stateful["pay_premium"], trace_stateless["pay_premium"], rtol=1e-4)
