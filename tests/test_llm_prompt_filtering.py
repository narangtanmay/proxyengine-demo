from llm_wrapper import ProxyEngineDualLens

RAW_TRACE_KEYS = ["opre", "actual_pay", "isin", "_traceability_map"]
RAW_PROPOSAL_KEYS = ["proposed_salary", "proposed_sti", "proposed_lti"]
DERIVED_TRACE_KEYS = ["reach_ratio", "multiple_of_median", "ratchet_triggered", "cluster_id"]


def _sample_isin(shared_sml_engine):
    return str(shared_sml_engine.data["isin"].iloc[0])


def test_filter_for_llm_strips_raw_trace_fields(shared_sml_engine):
    isin = _sample_isin(shared_sml_engine)
    trace = shared_sml_engine.get_evidence_trace(isin)

    filtered_trace, _ = ProxyEngineDualLens._filter_for_llm(trace, {})

    for key in RAW_TRACE_KEYS:
        assert key not in filtered_trace, f"raw field '{key}' leaked into LLM-bound trace"


def test_filter_for_llm_keeps_derived_trace_fields(shared_sml_engine):
    isin = _sample_isin(shared_sml_engine)
    trace = shared_sml_engine.get_evidence_trace(isin)

    filtered_trace, _ = ProxyEngineDualLens._filter_for_llm(trace, {})

    for key in DERIVED_TRACE_KEYS:
        assert key in filtered_trace, f"derived field '{key}' was wrongly dropped"


def test_filter_for_llm_strips_raw_proposal_fields():
    proposal = {
        "company_name": "Test AG",
        "exec_id": "Test Executive",
        "esg_linked": True,
        "agenda_item": "Agenda Item 6",
        "proposed_salary": 1234567.0,
        "proposed_sti": 2000000.0,
        "proposed_lti": 4500000.0,
    }

    _, filtered_proposal = ProxyEngineDualLens._filter_for_llm({}, proposal)

    for key in RAW_PROPOSAL_KEYS:
        assert key not in filtered_proposal, f"raw proposal field '{key}' leaked into LLM-bound proposal"
    assert filtered_proposal.get("company_name") == "Test AG"
    assert filtered_proposal.get("esg_linked") is True


def test_built_insight_prompt_excludes_raw_dollar_values(shared_sml_engine):
    """The strongest check: the actual prompt string sent to the LLM must not contain
    the raw, company-specific financial values, even though it's allowed to mention
    field *names* in the static CRITERION_GUIDE text."""
    isin = _sample_isin(shared_sml_engine)
    trace = shared_sml_engine.get_evidence_trace(isin)
    raw_actual_pay = trace["actual_pay"]
    raw_opre = trace["opre"]

    proposal = {
        "company_name": "Test AG",
        "exec_id": "Test Executive",
        "proposed_salary": 1234567.0,
        "proposed_sti": 2000000.0,
        "proposed_lti": 4500000.0,
    }

    dual_lens = ProxyEngineDualLens()
    content = dual_lens._build_insight_user_content("mom", trace, proposal)

    assert str(raw_actual_pay) not in content
    assert str(raw_opre) not in content
    assert "1234567.0" not in content
    assert "2000000.0" not in content
    assert "4500000.0" not in content
