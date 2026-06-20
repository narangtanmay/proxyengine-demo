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
    assert 'reach_ratio' in df.columns
    assert 'ratchet_flag' in df.columns
    assert 'cluster_median_pay' in df.columns
    assert 'multiple_of_median' in df.columns
    
    # Verify we can extract an evidence trace
    trace = engine.get_evidence_trace("DE0007664039", 2024)
    assert trace['company'] == "Volkswagen AG"
    assert trace['isin'] == "DE0007664039"
    assert trace['actual_pay'] > 0
    assert trace['cluster_median_pay'] > 0
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
    Programmatic Quality Test: Shadow Peer Cohesion & Separation
    Validation: Ensures K-Means on business-model physics (AT, ROA, Gearing) achieves
    satisfactory mathematical separation, preventing arbitrary peer groupings.
    """
    from sklearn.metrics import silhouette_score
    engine = ProxyEngineSML()
    df = engine.run_full_pipeline()
    
    features = ['asset_turnover_scaled', 'roa_scaled', 'gear_scaled']
    score = silhouette_score(df[features], df['shadow_peer_cluster'])
    
    # Asserts that the silhouette score is above the acceptable cohesion threshold
    assert score >= 0.30, f"K-Means shadow peer clustering quality degraded! Silhouette score: {score:.4f}"
