# ProxyEngine Specification

## 1. Context & Purpose
ProxyEngine is an automated, econometric auditing tool that evaluates German executive compensation against market baselines and governance rules. It combines an LLM-driven PDF extraction layer with a 7-stage deterministic Statistical Machine Learning (SML) pipeline. It outputs an NDA-safe Dual-Lens interface to simulate Proxy Advisor audits vs. Corporate Board compliance checks.

## Clarifications

### Session 2026-06-20
- Q: How should the 15-year ORBIS financial panel data and executive targets be ingested and stored for the SML engine? → A: Pre-filtered static CSV / Parquet datasets loaded locally.
- Q: How should the LLM-driven PDF remuneration report extraction layer operate given NDA constraints? → A: Use a remote LLM API (like Anthropic or OpenAI) exclusively for public, non-confidential PDFs, while sensitive financial database files remain strictly local.
- Q: In what language should the Dual-Lens interface and generated insights be displayed? → A: English only, retaining original German regulatory and corporate terminology (e.g., DCGK, VorstAG, Aufsichtsrat).
- Q: How should the SML econometric engine validate and display its statistical rigor during runtime? → A: Compute and display standard statistical diagnostics (standard errors, p-values, t-stats, R-squared) directly in the UI.
- Q: How should the SML engine handle cases where a selected company has missing or incomplete fundamental financial data? → A: Impute missing values using sector averages and display a clear "Imputed/Estimated" warning flag in the UI.

## 2. Requirements & Scope
- **Data Ingestion:** Ingest 15 years of ORBIS financial panel data and Executive Compensation targets from pre-filtered static CSV / Parquet datasets loaded locally.
- **PDF Upload POC:** Use a remote LLM API parsing layer (e.g., Anthropic or OpenAI) to extract standard components (salary, STI, LTI) from public, non-confidential PDF remuneration reports into our schema.
- **SML Engine:**
  - *Shadow Peers:* K-Means clustering on fundamental firm characteristics.
  - *Reach Ratio:* Lasso-Regularized Quantile Regression.
  - *Asymmetric Ratchets:* Fixed-effects dummy-variable panel regression.
  - *Statistical Rigor:* Compute and display standard statistical diagnostics (standard errors, p-values, t-stats, R-squared) directly in the UI.
- **Dual-Lens Output:**
  - *Auditor View:* Proxy Advisor recommendation (Activist Lens).
  - *Compliance View:* DCGK compliance warning (Corporate Board Lens).
  - *Localization:* Displayed in English, retaining original German regulatory and corporate terminology (e.g., DCGK, VorstAG, Aufsichtsrat).

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
- **Data Privacy:** Sensitive raw financials (e.g., those from Sciencehack TUM FA) remain strictly local. Only public, non-NDA PDF remuneration reports are processed via external generative AI APIs.
- **Input Validation:** PDF parsing must strictly adhere to the defined Pydantic schemas. Fallbacks should be in place if PDF text is illegible.
- **Missing Data Handling:** If ORBIS data is missing or incomplete, impute values using sector/industry averages and display a clear "Imputed/Estimated" warning flag in the UI.

## 6. Testing & Validation
- **Backtesting:** Validate the engine against known historical proxy shareholder revolts (e.g., Bayer 2020, Continental 2021).
