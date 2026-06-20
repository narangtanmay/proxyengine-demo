# ProxyEngine: Test Suite & Ground Truth Benchmarks (Agent Guide)

## 🤖 Attention AI Agents & Developers
This document explains the rationale, data sourcing, and execution strategy for the ProxyEngine test suite. When running, debugging, or extending the tests in the `tests/` directory, use this document as your primary domain knowledge context.

---

## 1. The Validation Strategy (Ground Truth)
In corporate finance, "fairness" is subjective. To mathematically validate the ProxyEngine Statistical Machine Learning (SML) pipeline without introducing bias, we use **historical Annual General Meeting (AGM) voting results** as our objective ground truth. 

Under the German implementation of **ARUG II (EU Shareholder Rights Directive II)**, listed companies must submit their remuneration reports to an annual shareholder vote ("Say-on-Pay"). If a package is rejected (typically driven by "Vote Against" recommendations from proxy advisors like ISS and Glass Lewis), it indicates a severe, mathematically provable governance anomaly. 

Our tests inject the financial profiles of these historical scandals into the SML engine to verify that our algorithms flag the *exact same anomalies* that caused the real-world shareholder revolts.

---

## 2. The Test Cases & Sourcing

### Test 1: Bayer AG (2020) - The Asymmetric Ratchet
*   **Sourced From:** 2020 Bayer AG Annual General Meeting results and subsequent ISS proxy voting recommendations.
*   **The Historical Reality:** Shareholders delivered a historic rebuke, with over 75% voting *against* the remuneration report. The board paid out high bonuses despite the disastrous Monsanto acquisition destroying billions in market capitalization (plummeting ROA and TSR).
*   **What the Agent Tests:** `test_bayer_2020_asymmetric_ratchet` validates the SML Panel Regression. It ensures the model outputs `ratchet_triggered: True` when it detects that executive pay remained insulated while firm performance (ROA) severely contracted.

### Test 2: Software AG (2022) - The "Reach" Anomaly
*   **Sourced From:** 2022 Software AG AGM results and governance backlash reports.
*   **The Historical Reality:** Shareholders rejected the remuneration report due to outsized Long-Term Incentive (LTI) packages and complex target setting that misaligned with the company's mid-cap (MDAX/TecDAX) scale.
*   **What the Agent Tests:** `test_software_ag_2022_reach_anomaly` validates the Lasso-Regularized Quantile Regression. It proves the engine calculates a massive `reach_ratio` (e.g., > 2.0x), mathematically demonstrating to the LLM that the CEO was being paid like a firm twice its actual operating revenue.

### Test 3: The Secrecy Premium (DCGK Compliance)
*   **Sourced From:** DCGK (German Corporate Governance Code) guidelines regarding individual disclosure of board compensation.
*   **The Historical Reality:** Companies that legally opt out of individualized disclosure (using the `opting_out` reporting loophole) face automatic proxy advisor scrutiny and lowered governance scores.
*   **What the Agent Tests:** `test_secrecy_premium_flag` ensures the data ingestion pipeline successfully passes the `opting_out` boolean through the SML engine into the final `EvidenceTrace` JSON, guaranteeing the LLM triggers a compliance warning.

---

## 3. Execution & Extension Instructions for Agents

**Running the Test Suite:**
Agents should run the following command to verify the SML pipeline's integrity before pushing code changes:
```bash
python3 -m pytest tests/test_historical_revolts.py -v
```

**Adding New Tests:**
If new ARUG II proxy data becomes available, agents should:
1. Identify a company that received a severe "Say-on-Pay" rejection.
2. Extract their `opre` (Operating Revenue), `roa` (Return on Assets), `gear` (Leverage), and `total_comp` for the year of the vote and the preceding year.
3. Inject the data into the `generate_background_market_data()` mock panel.
4. Assert that the SML engine triggers the correct mathematical anomaly (Reach, Ratchet, or Hidden Stretch) matching the real-world proxy advisor complaint.
