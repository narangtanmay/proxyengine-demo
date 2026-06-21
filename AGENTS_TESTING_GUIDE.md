# ProxyEngine: Test Suite & Ground Truth Benchmarks (Agent Guide)

## Attention AI Agents & Developers

This document explains the rationale, data sourcing, and execution strategy for the ProxyEngine test suite. When running, debugging, or extending tests in `tests/`, use this document as your primary domain context.

---

## 1. Validation Strategy (Ground Truth)

In corporate finance, "fairness" is subjective. To mathematically validate the ProxyEngine Statistical Machine Learning (SML) pipeline without introducing bias, we use **historical Annual General Meeting (AGM) voting results** as objective ground truth.

Under the German implementation of **ARUG II (EU Shareholder Rights Directive II)**, listed companies must submit their remuneration reports to an annual shareholder vote ("Say-on-Pay"). When a package is rejected (typically driven by "Vote Against" recommendations from proxy advisors like ISS and Glass Lewis), it indicates a severe, mathematically provable governance anomaly.

Our tests inject the financial profiles of these historical scandals into the SML engine and verify that the algorithms flag the **same anomaly types** that caused real-world shareholder revolts.

---

## 2. Historical Ground-Truth Test Cases

These live in [`tests/test_historical_revolts.py`](tests/test_historical_revolts.py).

### Test 1: Allianz SE (2025) — LTI Structural Imbalance

*   **Sourced from:** 2025 Allianz SE AGM / ISS proxy voting recommendations on Agenda Item 7 (remuneration policy).
*   **Historical reality:** ISS recommended AGAINST the remuneration policy due to an excessive LTI target multiplier relative to fixed base salary, breaching DCGK G.1 guidance.
*   **What the test validates:** `test_allianz_2025_lti_structural_imbalance` injects an Allianz 2025 profile (LTI = €8M, base salary = €1.8M) into the panel and asserts `lti_vs_salary_ratio > 4.0` in the returned `EvidenceTrace`.

### Test 2: DHL Group (2024) — Pay-for-Performance Disconnect

*   **Sourced from:** 2024 DHL Group AGM pushback on the remuneration report (Agenda Item 7).
*   **Historical reality:** Shareholders objected to STI payout increases while ROA contracted materially year-over-year.
*   **What the test validates:** `test_dhl_2024_pay_performance_disconnect` injects a 2023–2024 two-year panel (STI up, ROA down) and asserts `ratchet_triggered is True`.

---

## 3. Full Test Suite Map

Always use the virtualenv interpreter from [`CLAUDE.md`](CLAUDE.md):

```bash
# Primary regression suite (historical AGM cases)
/home/tanmay/Desktop/science_hack/proxyengine/venv/bin/pytest tests/test_historical_revolts.py -v

# Full suite
/home/tanmay/Desktop/science_hack/proxyengine/venv/bin/pytest tests/ -v
```

| File | Focus | Key tests |
|------|-------|-----------|
| [`tests/test_historical_revolts.py`](tests/test_historical_revolts.py) | AGM ground-truth benchmarks | Allianz 2025 LTI ratio, DHL 2024 ratchet |
| [`tests/test_proxy_engine.py`](tests/test_proxy_engine.py) | Pipeline integrity, PDF fallback, dual-lens reports, K-Means quality, chat routing | `test_sml_engine_pipeline`, `test_dual_lens_report_generation`, `test_kmeans_shadow_peer_quality` |
| [`tests/test_llm_prompt_filtering.py`](tests/test_llm_prompt_filtering.py) | NDA-safe LLM prompt allowlist | Strips `opre`, `actual_pay`, `proposed_salary` etc. before prompts |
| [`tests/test_treadmill_decomposition.py`](tests/test_treadmill_decomposition.py) | Oaxaca-Blinder treadmill math | `test_treadmill_oaxaca_decomposition` |
| [`tests/test_stateless_parity.py`](tests/test_stateless_parity.py) | Cached vs live SML scoring parity | `test_sml_stateless_parity` |

Shared fixtures are defined in [`tests/conftest.py`](tests/conftest.py):

*   `shared_sml_engine` — session-scoped; fits the full SML pipeline once per test run.
*   `shared_dual_lens` — session-scoped `ProxyEngineDualLens` instance.

---

## 4. LLM Guardrails & Prompt Filtering

The dual-lens LLM layer must **never** receive raw proprietary euro amounts. Filtering is enforced in [`src/llm_wrapper.py`](src/llm_wrapper.py) via:

*   **`TRACE_ALLOWLIST`** — derived ratios and flags only (`reach_ratio`, `multiple_of_median`, `ratchet_triggered`, `lti_vs_salary_ratio`, etc.). Raw fields like `opre`, `actual_pay`, and `isin` are stripped.
*   **`PROPOSAL_ALLOWLIST`** — `company_name`, `exec_id`, `esg_linked`, `agenda_item` only. Raw `proposed_salary`, `proposed_sti`, `proposed_lti` are stripped.

[`tests/test_llm_prompt_filtering.py`](tests/test_llm_prompt_filtering.py) verifies:

1. Raw trace fields do not appear in filtered output.
2. Derived trace fields are preserved.
3. Raw proposal euro amounts do not appear in filtered output.
4. Built insight prompt strings exclude raw dollar values entirely.

### Wizard-of-Oz fallback guardrail

[`tests/conftest.py`](tests/conftest.py) installs an **autouse** fixture that **fails any test** that silently hits an offline LLM mock fallback unless explicitly marked:

```python
@pytest.mark.allow_fallback_mock
def test_something_that_uses_fallback():
    ...
```

This prevents integration tests from passing while the LLM layer degrades to local templates without notice.

---

## 5. Execution & Extension Instructions

### Before pushing SML or LLM changes

```bash
/home/tanmay/Desktop/science_hack/proxyengine/venv/bin/pytest tests/test_historical_revolts.py -v
/home/tanmay/Desktop/science_hack/proxyengine/venv/bin/pytest tests/test_llm_prompt_filtering.py -v
```

### Adding a new historical revolt test

1. Identify a company that received a severe Say-on-Pay rejection under ARUG II.
2. Extract `opre`, `roa`, `gear`, `salary`, `sti`, `lti`, and `total_comp` for the vote year (and prior year if testing ratchets).
3. Append rows to a copy of `shared_sml_engine.data` via `pd.concat`, instantiate a fresh `ProxyEngineSML(df_combined)`, and call `run_full_pipeline()`.
4. Assert the correct flag in `engine.get_evidence_trace(isin, year)` — e.g. `reach_ratio`, `ratchet_triggered`, or `lti_vs_salary_ratio`.
5. Add the test to `tests/test_historical_revolts.py` with a docstring citing the AGM ground truth.

Do **not** reference removed helpers such as `generate_background_market_data()` — they are not part of this codebase.
