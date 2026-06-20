# ProxyEngine Specification

## 1. Context & Purpose
ProxyEngine is an automated, econometric auditing tool that evaluates German executive compensation against market baselines and governance rules. It combines an LLM-driven PDF extraction layer with a 7-stage deterministic Statistical Machine Learning (SML) pipeline. It outputs an NDA-safe Dual-Lens interface to simulate Proxy Advisor audits vs. Corporate Board compliance checks.

## 2. Requirements & Scope
- **Data Ingestion:** Ingest 15 years of ORBIS financial panel data and Executive Compensation targets.
- **PDF Upload POC:** Mock an LLM parsing layer that takes an unstructured PDF remuneration report and outputs standard components (salary, STI, LTI) into our schema.
- **SML Engine:**
  - *Shadow Peers:* K-Means clustering on fundamental firm characteristics.
  - *Reach Ratio:* Lasso-Regularized Quantile Regression.
  - *Asymmetric Ratchets:* Fixed-effects dummy-variable panel regression.
- **Dual-Lens Output:**
  - *Auditor View:* Proxy Advisor recommendation (Activist Lens).
  - *Compliance View:* DCGK compliance warning (Corporate Board Lens).

## 3. Architecture & Design
The architecture is structured sequentially to prevent data dredging and hallucinations:
1. **Data Layer:** `opre`, `roa`, `gear`, `total_comp`. 
2. **Math Layer:** Isolated execution of K-Means and Quantile regressions. Outputs the "EvidenceTrace".
3. **LLM Translation Layer:** Only ingests the EvidenceTrace JSON. Uses specific system prompts for the Dual-Lens interface.
4. **UI Layer:** A Streamlit/React frontend providing the "Wargaming Toggle" (Auditor vs Compliance) and visualizing the Reach scatterplot.

## 4. Interfaces & Data Flow
**EvidenceTrace Schema:**
```json
{
  "company": "string",
  "reach_ratio": "float",
  "ratchet_triggered": "boolean",
  "secrecy_premium_flag": "boolean",
  "lti_vs_salary_ratio": "float"
}
```

## 5. Security & Error Handling
- **Data Privacy:** Raw financials remain local.
- **Input Validation:** PDF parsing must strictly adhere to the defined Pydantic schemas. Fallbacks should be in place if PDF text is illegible.

## 6. Testing & Validation
- **Backtesting:** Validate the engine against known historical proxy shareholder revolts (e.g., Bayer 2020, Continental 2021).
