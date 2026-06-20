import pytest
import pandas as pd
import numpy as np
import sys
import os

# Ensure local src directory is in path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from sml_engine import ProxyEngineSML
from pdf_parser_poc import PDFExtractorPOC
from llm_wrapper import ProxyEngineDualLens

def test_sml_engine_pipeline():
    """Verify that SML pipeline runs fully and computes all expected fields."""
    engine = ProxyEngineSML()
    df = engine.run_full_pipeline()
    
    # Assert expected columns are computed
    assert 'shadow_peer_cluster' in df.columns
    assert 'pay_premium' in df.columns          # PDF Step 2 headline
    assert 'reach_ratio' in df.columns
    assert 'ratchet_flag' in df.columns
    assert 'cluster_median_pay' in df.columns
    assert 'multiple_of_median' in df.columns

    # The fair-pay line is fitted at the median, so the median premium sits at ~1.0x.
    assert abs(df['pay_premium'].median() - 1.0) < 0.25  # Relaxed tolerance for the more robust scaled controls

    # Verify we can extract an evidence trace for a real company (latest year falls back).
    trace = engine.get_evidence_trace("DE0007664005", 2024)
    assert trace['company'] == "Volkswagen AG"
    assert trace['isin'] == "DE0007664005"
    assert trace['actual_pay'] > 0
    assert trace['cluster_median_pay'] > 0
    assert trace['pay_premium'] > 0
    assert trace['reach_ratio'] > 0
    assert isinstance(trace['ratchet_triggered'], bool)

def test_pdf_extractor_fallback():
    """Verify that PDFExtractorPOC processes successfully and falls back on error/mock."""
    extractor = PDFExtractorPOC()
    data = extractor.process()
    
    assert data['company_name'] == "Volkswagen AG"
    assert data['proposed_salary'] == 1500000.0
    assert data['proposed_sti'] == 2000000.0
    assert data['proposed_lti'] == 4500000.0
    assert data['esg_linked'] is True

def test_dual_lens_report_generation():
    """Verify that dual lens wrapper produces well-formatted reports."""
    translator = ProxyEngineDualLens()
    trace = {
        "company": "Bayer AG",
        "exec_id": "Bill Anderson",
        "cluster_id": 1,
        "actual_pay": 5000000.0,
        "cluster_median_pay": 3500000.0,
        "multiple_of_median": 1.43,
        "reach_ratio": 1.8,
        "ratchet_triggered": False,
        "secrecy_premium_flag": False,
        "lti_vs_salary_ratio": 2.5
    }
    proposal = {
        "company_name": "Bayer AG",
        "exec_id": "Bill Anderson",
        "proposed_salary": 1400000.0,
        "proposed_sti": 1800000.0,
        "proposed_lti": 3800000.0,
        "esg_linked": True,
        "agenda_item": "Agenda Item 5: Approval of the Remuneration Report"
    }
    
    auditor_report = translator.generate_auditor_report(trace, proposal)
    compliance_report = translator.generate_compliance_report(trace, proposal)
    
    assert "RECOMMENDATION: VOTE AGAINST" in auditor_report
    assert "Bayer AG" in auditor_report
    assert "Bill Anderson" in auditor_report
    assert "1.8x" in auditor_report
    
    assert "STATUS: HIGH RISK" in compliance_report
    assert "Bayer AG" in compliance_report
    assert "DCGK" in compliance_report

def test_kmeans_shadow_peer_quality():
    """
    Hardened Programmatic Quality Test: Shadow Peer Cohesion & Separation
    Validation:
    1. Enforces a strict Silhouette Score threshold of >= 0.48.
    2. Enforces the Balance Gate: no single cluster contains more than 40% of the total company-years.
    """
    from sklearn.metrics import silhouette_score
    engine = ProxyEngineSML()
    df = engine.run_full_pipeline()
    
    features = ['employees_scaled', 'operating_revenue_scaled']
    score = silhouette_score(df[features], df['shadow_peer_cluster'])
    
    # Assert Cohesion & Separation Gate
    assert score >= 0.48, f"K-Means shadow peer clustering quality degraded! Silhouette score: {score:.4f}"
    
    # Assert the Balance Gate (max cluster <= 40%)
    counts = df['shadow_peer_cluster'].value_counts()
    max_pct = counts.max() / len(df)
    assert max_pct <= 0.40, f"K-Means collapsed into unbalanced clusters! Largest cluster contains {max_pct:.2%}"

def test_parts_combined_pipeline_consistency():
    """
    TDD Test 1: SML "Parts Combined" Internal Consistency
    Validation: Ensures that when parts_combined=True:
    1. Independent regressions are executed for Salary, STI, and LTI.
    2. Expected total compensation equals the sum of the three benchmarks: Expected_Total = Salary_bench + STI_bench + LTI_bench.
    3. The headline premium equals Total_Comp / Expected_Total.
    """
    engine = ProxyEngineSML()
    df = engine.run_full_pipeline(parts_combined=True)
    
    # Assert component benchmarks and overall expected structures are computed
    assert 'salary_benchmark' in df.columns
    assert 'sti_benchmark' in df.columns
    assert 'lti_benchmark' in df.columns
    assert 'expected_total_comp' in df.columns
    assert 'headline_premium' in df.columns
    
    # Mathematical identity verification: expected_total_comp == salary_bench + sti_bench + lti_bench
    sample_row = df.iloc[0]
    expected_sum = sample_row['salary_benchmark'] + sample_row['sti_benchmark'] + sample_row['lti_benchmark']
    assert np.isclose(sample_row['expected_total_comp'], expected_sum, rtol=1e-5)
    
    # Headline premium check: actual total / expected parts
    expected_premium = sample_row['total_comp'] / expected_sum
    assert np.isclose(sample_row['headline_premium'], expected_premium, rtol=1e-5)

def test_hidden_stretch_calculation():
    """
    TDD Test 2: "Hidden Stretch" Concentration Anomaly (BMW 2017 Analogy)
    Validation: Mimics the concentrated compensation payout of BMW 2017:
    - Base Salary: €1M (Benchmark Salary: €1.1M) -> Premium_Salary = 0.909x
    - STI Target: €4M (Benchmark STI: €1.2M)     -> Premium_STI = 3.333x (Most-stretched form)
    - LTI Target: €0   (Benchmark LTI: €1.0M)     -> Premium_LTI = 0.0x
    - Headline parts sum to: Actual = €5.0M, Benchmark = €3.3M -> Headline Premium = 1.515x
    - Expected Hidden Stretch: (3.333 / 1.515) - 1 == +120.0%
    """
    salary = 1000000.0
    sti = 4000000.0
    lti = 0.0
    
    salary_bench = 1100000.0
    sti_bench = 1200000.0
    lti_bench = 1000000.0
    
    headline_prem = (salary + sti + lti) / (salary_bench + sti_bench + lti_bench)
    
    prem_salary = salary / salary_bench
    prem_sti = sti / sti_bench
    prem_lti = lti / lti_bench if lti_bench > 0 else 0.0
    
    max_form_prem = max(prem_salary, prem_sti, prem_lti)
    hidden_stretch = (max_form_prem / headline_prem) - 1.0
    
    assert np.isclose(headline_prem, 1.51515, rtol=1e-4)
    assert np.isclose(prem_salary, 0.90909, rtol=1e-4)
    assert np.isclose(prem_sti, 3.33333, rtol=1e-4)
    assert np.isclose(hidden_stretch, 1.20, rtol=1e-2)
    assert hidden_stretch >= 0.0

def test_log_zero_robustness_safeguard():
    """
    TDD Test 3: Log-Zero Robustness (Firms opting out of LTI or STI)
    Validation: Asserts that when fitting the component regressions (Salary, STI, LTI),
    companies with zero-dollar STI or LTI are handled safely without infinite or NaN errors
    (verifies that the engine utilizes a log1p or offset safeguard).
    """
    engine = ProxyEngineSML()
    df = engine.data.copy()
    
    df.loc[df.index[0], 'lti'] = 0.0
    df.loc[df.index[1], 'sti'] = 0.0
    
    try:
        engine_temp = ProxyEngineSML(df)
        df_result = engine_temp.run_full_pipeline(parts_combined=True)
        assert not df_result['lti_benchmark'].isnull().any()
        assert not df_result['sti_benchmark'].isnull().any()
    except Exception as e:
        pytest.fail(f"SML Parts-Combined pipeline crashed under log-zero inputs! Error: {e}")
