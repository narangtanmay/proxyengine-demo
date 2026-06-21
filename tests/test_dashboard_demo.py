import json


def _extract_trace_blob(prompt_text: str) -> dict:
    marker_a = "Deterministic SML evidence trace:\n"
    marker_b = "\n\nRemuneration proposal details:"
    start = prompt_text.index(marker_a) + len(marker_a)
    end = prompt_text.index(marker_b)
    return json.loads(prompt_text[start:end])


def test_bayer_sap_dashboard_trace_sanity(shared_sml_engine):
    for isin in ["DE000BAY0017", "DE0007164600"]:
        trace = shared_sml_engine.get_evidence_trace(isin, 2024)
        assert "cluster_median_pay" in trace and trace["cluster_median_pay"] > 0
        assert "multiple_of_median" in trace and trace["multiple_of_median"] > 0
        assert "pay_premium" in trace and trace["pay_premium"] > 0
        assert "reach_ratio" in trace and trace["reach_ratio"] > 0

        expected = trace["actual_pay"] / trace["cluster_median_pay"]
        assert abs(trace["multiple_of_median"] - expected) < 1e-9


def test_insight_prompt_uses_real_trace_values(shared_sml_engine, shared_dual_lens):
    trace = shared_sml_engine.get_evidence_trace("DE0007164600", 2024)
    proposal = {"company_name": trace["company"], "exec_id": trace["exec_id"], "esg_linked": False}
    prompt = shared_dual_lens._build_insight_user_content("mom", trace, proposal)
    prompt_trace = _extract_trace_blob(prompt)

    assert prompt_trace["multiple_of_median"] > 1.05
    assert prompt_trace["reach_ratio"] > 1.05
    assert prompt_trace["pay_premium"] > 1.05
