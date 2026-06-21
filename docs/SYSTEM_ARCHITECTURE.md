# ProxyEngine: System Architecture & API Specification
**Definitive Ground Truth & Developer Guide**

*This document is generated and maintained in alignment with the `codebase-documenter` standard. It establishes the single, mathematically and architecturally validated "ground truth" of the ProxyEngine (Say-on-Pay) platform.*

---

## 1. Product Context & Reconciled Pitch

### The Core Vision
German executive compensation is highly complex, opaque, and historically insulated from market pressure. While corporate boards leverage self-selected benchmark groups to artificially inflate pay (the "Lake Wobegon" effect), institutional investors and activist hedge funds lack objective tools to identify rent extraction, flag structural governance imbalances, or stress-test shareholder resolutions under ARUG II.

### The Pitch
> "Before launching a proxy fight over executive compensation, institutional investors need mathematically bulletproof evidence of rent extraction and the ability to anticipate the corporate board's legal defense.
> 
> We built **ProxyEngine**, an Adversarial AI platform for Say-on-Pay governance analysis. It ingests German corporate data, uses regularized econometric models to define expected compensation, and mathematically isolates executive rent extraction (such as 'Asymmetric Ratchets' and 'Reach Ratios'). Finally, an NDA-compliant LLM translates these complex statistical flags into a dual-lens adversarial brief: generating both the activist's attack thesis (Auditor Mode) and predicting the board's DCGK compliance defense (Defender Mode)."

---

## 2. Core SML Pipeline & Mathematical Methodology

The statistical core of ProxyEngine is a 7-stage deterministic Statistical Machine Learning (SML) pipeline implemented in `src/sml_engine.py`. Rather than relying on black-box predictive models, it uses robust, interpretable econometrics validated against empirical corporate finance literature.

```
                  [ Raw Data Panel (ORBIS) ]
                              │
                              ▼
                   [ Stage 0: Prep & Log ]
                              │
                              ▼
           [ Stage 1: Precomputed Peer Clustering ]
                              │
                              ▼
         [ Stage 2: Median Quantile Regression Baseline ]
                              │
                              ▼
                [ Stage 3: Reach Ratio Isolation ]
                              │
                              ▼
              [ Stage 4: Oaxaca-Blinder Treadmill ]
                              │
                              ▼
           [ Stage 5: Asymmetric Ratchet Panel OLS ]
                              │
                              ▼
              [ Stage 6: ISS & Statutory Audits ]
```

### Stage 0: Data Cleaning & Preprocessing
*   **Annualization:** Executive tenures of partial-year length are annualized to a 365-day basis:
    $$\text{Pay}_{\text{ann}} = \text{Pay}_{\text{raw}} \times \left(\frac{365}{\text{days}}\right)$$
*   **Real Deflation:** Nominal compensation values are deflated using the Consumer Price Index (CPI) to remove historical inflation illusion and isolate real purchasing power:
    $$\text{Pay}_{\text{real}} = \frac{\text{Pay}_{\text{ann}}}{\left(\text{CPI}_t / \text{CPI}_{\text{base}}\right)}$$

### Stage 1: Objective "Shadow Peer" Clustering
To reject arbitrary industry classifications that boards manipulate, we group companies by their economic fundamentals (physics of the business model) using unsupervised K-Means clustering.
*   **Cluster Features:** 
    1.  **Scale / Size:** `log_size` (Log of Operating Revenue, `log(opre)`)
    2.  **Efficiency / Performance:** `roa` (Return on Assets)
    3.  **Risk / Leverage:** `gear` (Gearing Ratio)
*   **Usage:** Real panel uses precomputed labels verbatim; newly uploaded remuneration PDFs are dynamically mapped to one of the 7 clusters using nearest-centroid Euclidean distance in the scaled feature space.

### Stage 2: Fair-Pay Baseline (Quantile Regression)
Models expected median compensation across the peer group using a **Lasso-Regularized Quantile Regression** at the conditional median ($\tau = 0.5$):
$$Q_{0.5}(\log(\text{pay}_{it})) = \alpha + \beta \log(\text{opre}_{it}) + \gamma_1 \text{roa}_{it} + \gamma_2 \text{gear}_{it} + \delta_t$$
where $\delta_t$ is the year fixed effect.
*   **LAD Fitting:** Least Absolute Deviations (LAD) prevent megacap payout outliers from dragging the baseline upward.
*   **Elasticity Bound:** Size elasticity ($\beta$) is verified to converge tightly to $\approx 0.30$ (in accordance with *Gabaix & Landier, 2008*).

### Stage 3: The Gap as "Reach" Ratio
Isolates unexplained executive rent extraction:
$$\varepsilon_{it} = \log(\text{pay}_{it}) - \widehat{\log(\text{pay}_{it})}$$
*   **Headline Premium:** $\exp(\varepsilon_{it})$ (multiple above/expected fair pay).
*   **Reach Ratio:** Translates residual rent into size-equivalent scale:
    $$\text{Reach}_{it} = \exp\left(\frac{\varepsilon_{it}}{\beta}\right)$$
    *Interpretation:* "The CEO is paid as if leading a firm $X$ times their company's actual size."

### Stage 4: Market-wide Drift ("The Treadmill")
Traces the year fixed effects $\delta_t$ over time to isolate real upward drift of the baseline, proving whether executive pay trends upward independently of corporate expansion.

### Stage 5: Asymmetric Ratchets ("Pay for Luck")
Determines whether executive pay is decoupled from downside risk (citing *Garvey & Milbourn, 2006*):
$$\Delta \log(\text{pay}_{it}) = \alpha + \beta_{\uparrow} \Delta \text{roa}_{it}^+ + \beta_{\downarrow} \Delta \text{roa}_{it}^-$$
*   **Heuristic Flag:** An individual firm-year triggers a ratchet flag if:
    $$\Delta \text{Pay} > 1\% \quad \text{AND} \quad \Delta \text{ROA} < -0.5\%$$
*   **Panel Analysis:** Systemic asymmetry is verified across the cohort; fires if $\beta_{\uparrow} \ge 2.0 \times |\beta_{\downarrow}|$.

### Stage 6: ISS & Statutory Audits
*   **Multiple of Median (MoM):** compares actual pay against the objective shadow-peer cluster median pay:
    $$\text{MoM} = \frac{\text{Total Pay}}{\text{Cluster Median Pay}}$$
*   **AktG § 87 Audit:** Asserts that the variable Long-Term Incentive (LTI) target allocation does not breach healthy ratios relative to fixed base salary (flags if `lti_vs_salary_ratio > 4.0`).

---

## 3. System Architecture & Ingestion Flow

The system isolates the Large Language Model (LLM) from raw financial data manipulation using a strict **EvidenceTrace Security Boundary** to prevent hallucinations.

```
┌─────────────────┐      (Pydantic)      ┌─────────────────────────┐
│  Remuneration   │─────────────────────>│ RemunerationProposal    │
│  Report PDF     │                      │ (Salary, STI, LTI JSON) │
└─────────────────┘                      └─────────────────────────┘
                                                      │
                                                      ▼ (Stateless Evaluation)
                                         ┌─────────────────────────┐
                                         │ SML Econometric Engine  │
                                         └─────────────────────────┘
                                                      │
                                                      ▼ (Generates Ratios)
                                         ┌─────────────────────────┐
                                         │ EvidenceTrace JSON      │
                                         │ (full trace for UI/API) │
                                         └─────────────────────────┘
                                                      │
                                                      ▼ (_filter_for_llm allowlist)
                                         ┌─────────────────────────┐
                                         │ NDA-Safe Prompt Payload │
                                         │ (ratios & flags only)   │
                                         └─────────────────────────┘
                                                      │
                                                      ▼ (Prompt Injection)
                                         ┌─────────────────────────┐
                                         │ Dual-Lens LLM Translator│
                                         └─────────────────────────┘
                                            │                   │
                     (Auditor Mode)         │                   │         (Defender Mode)
                     ┌──────────────────────┘                   └──────────────────────┐
                     ▼                                                                 ▼
      ┌─────────────────────────────┐                                   ┌─────────────────────────────┐
      │ Proxy Vote Recommendation   │                                   │ Board Compliance Defense    │
      │ (ruthless attack brief)     │                                   │ (DCGK arguments & remedies) │
      └─────────────────────────────┘                                   └─────────────────────────────┘
```

### API vs LLM Data Boundary

Dashboard and upload endpoints return the **full** `EvidenceTrace` JSON, including raw proprietary fields (`opre`, `actual_pay`, `isin`, `cluster_median_pay`, etc.) so the frontend can render charts and euro-denominated labels.

Before any data reaches a third-party LLM API, [`src/llm_wrapper.py`](src/llm_wrapper.py) applies `_filter_for_llm()`:

| Layer | Trace fields | Proposal fields |
|-------|--------------|-----------------|
| **UI / REST API** | Full trace (all computed + raw columns) | Full `RemunerationProposal` including euro amounts |
| **LLM prompts** | `TRACE_ALLOWLIST` only — ratios, flags, benchmarks | `PROPOSAL_ALLOWLIST` only — `company_name`, `exec_id`, `esg_linked`, `agenda_item` |

Stripped trace fields include: `opre`, `actual_pay`, `isin`, `_traceability_map`. Stripped proposal fields include: `proposed_salary`, `proposed_sti`, `proposed_lti`.

Tests in [`tests/test_llm_prompt_filtering.py`](../tests/test_llm_prompt_filtering.py) enforce this boundary.

---

## 3.1 Frontend Architecture

The production UI is a **single-page custom HTML dashboard** — not a Vite/React build, not Streamlit.

| Asset | Path | Role |
|-------|------|------|
| Dashboard template | [`src/frontend/Pay Governance Dashboard.dc.html`](../src/frontend/Pay Governance Dashboard.dc.html) | Three-step workflow: Firm & Package → Criteria → Report |
| Templating engine | [`src/frontend/support.js`](../src/frontend/support.js) | `DCLogic` reactive engine (`sc-if`, `sc-for`, `{{ }}` bindings) |
| Static hosting | [`src/backend/main.py`](../src/backend/main.py) | `GET /` serves the HTML; `GET /support.js` serves the engine |

**Runtime stack:** React 18 and Plotly are loaded via CDN inside the HTML file. There is no `npm run build` step.

**Page 3 (Automated Report) rule:** All econometric regression curves and model diagnostics on the report page must be driven by backend endpoints (`/api/model`, `/api/companies/{isin}/dashboard`, `/api/companies/{isin}/peers`) — not recomputed with client-side OLS on hardcoded peer presets.

**Workflow steps:**

1. **Step 1 — Firm & Package:** Company picker, compensation inputs (base / STI / LTI).
2. **Step 2 — Criteria:** Select ISS-style evaluation questions (MoM, SML premium, ratchet, reach, disclosure, LTI ratio).
3. **Step 3 — Report:** KPI ribbon, dual-lens insights, question-specific visualizations (Plotly scatter, gauges, peer table).

---

## 4. REST API Specification

### 1. Get Available Companies
Retrieve German corporations in the active dataset.

*   **Endpoint:** `GET /api/companies`
*   **Response Headers:** `Content-Type: application/json`
*   **Example Response:**
```json
[
  {"id": "DE0007664005", "name": "Volkswagen AG"},
  {"id": "DE000BAY0017", "name": "Bayer AG"},
  {"id": "DE0005439004", "name": "Continental AG"}
]
```

### 2. Get Ozkan Next-Year Predictions (Single Company)

Returns precomputed Ozkan-model cash, LTI, and total compensation forecasts for one firm.

*   **Endpoint:** `GET /api/companies/{isin}/ozkan`
*   **Response Headers:** `Content-Type: application/json`
*   **Example Response:**
```json
{
  "isin": "DE0007664005",
  "name": "Volkswagen",
  "peer": "Peer_C4",
  "index": "DAX",
  "median_pay_k": 5426.0,
  "median_opre_m": 252392.0,
  "pred": {
    "company": "Volkswagen",
    "peer": "Peer_C4",
    "fund_year": 2021,
    "pred_year": 2022,
    "cash_k": 2563.0,
    "lti_k": 1867.0,
    "total_k": 4182.0
  }
}
```

### 3. Get Model Diagnostics
Retrieve the global SML quantile regression diagnostics and sample-wide asymmetric ratchet test results.

*   **Endpoint:** `GET /api/model`
*   **Response Headers:** `Content-Type: application/json`
*   **Example Response:**
```json
{
  "diagnostics": {
    "pseudo_r2": 0.584,
    "size_beta": 0.287,
    "size_se": 0.015,
    "size_tstat": 19.13,
    "size_pvalue": 0.0,
    "roa_beta": 1.45,
    "gear_beta": -0.12,
    "n_obs": 3750
  },
  "ratchet": {
    "good_year_slope": 0.41,
    "bad_year_slope": 0.38,
    "n_good": 1820,
    "n_bad": 1790,
    "fires": false
  },
  "n_clusters": 7,
  "year_min": 2010,
  "year_max": 2024
}
```

### 4. Get Oaxaca-Blinder Treadmill Decomposition

Returns precomputed Route B treadmill decomposition (fundamentals vs market drift).

*   **Endpoint:** `GET /api/treadmill`
*   **Response Headers:** `Content-Type: application/json`
*   **Example Response:**
```json
{
  "year_first": 2010,
  "year_last": 2024,
  "delta_log_pay": 0.42,
  "fundamentals_component": 0.28,
  "treadmill_component": 0.14,
  "treadmill_share_pct": 33.3,
  "b0_beta_size": 0.29,
  "bT_beta_size": 0.31
}
```

### 5. Get Shadow-Peer Cluster Summary
Retrieve size, pay levels, and premium spreads grouped within each of the precomputed shadow-peer clusters.

*   **Endpoint:** `GET /api/clusters`
*   **Response Headers:** `Content-Type: application/json`
*   **Example Response:**
```json
[
  {
    "cluster_id": 4,
    "n_firms": 42,
    "n_firm_years": 510,
    "median_opre": 31200000000.0,
    "median_roa": 0.062,
    "median_gear": 0.45,
    "median_pay": 5400000.0,
    "median_premium": 1.02,
    "p90_premium": 1.42,
    "share_above_benchmark": 0.52,
    "top_firm": "Volkswagen AG",
    "top_firm_premium": 1.78
  }
]
```

### 6. Get Company Dashboard Metrics
Retrieve specific EvidenceTrace statistical anomalies for a given corporation and year.

*   **Endpoint:** `GET /api/companies/{isin}/dashboard`
*   **Query Parameters:** `year` (integer, optional)
*   **Example Request:**
```bash
curl -X GET "http://localhost:8000/api/companies/DE0007664005/dashboard?year=2024"
```
*   **Example Response:**
```json
{
  "company": "Volkswagen AG",
  "isin": "DE0007664005",
  "exec_id": "Oliver Blume",
  "year": 2024,
  "cluster_id": 4,
  "opre": 322300000000.0,
  "actual_pay": 8000000.0,
  "cluster_median_pay": 5800000.0,
  "multiple_of_median": 1.379,
  "pay_premium": 1.154,
  "reach_ratio": 1.623,
  "ratchet_triggered": true,
  "secrecy_premium_flag": false,
  "lti_vs_salary_ratio": 3.0
}
```

> **Note:** This response includes raw euro fields for UI rendering. The LLM layer strips `opre`, `actual_pay`, and `isin` via `TRACE_ALLOWLIST` before building prompts.

### 7. Get Shadow-Peer Scatter Data

Returns latest firm-year records for all companies in the dataset, with an `is_peer` flag for members of the subject company's shadow-peer cluster. Used to populate the Step 3 SML scatter plot.

*   **Endpoint:** `GET /api/companies/{isin}/peers`
*   **Query Parameters:** `year` (integer, optional; default `2024`)
*   **Example Response:**
```json
[
  {
    "isin": "DE0007100000",
    "name": "Mercedes-Benz Group",
    "exec": "Ola Källenius",
    "opre": 145.6,
    "roa": 6.1,
    "base": 2.1,
    "sti": 3.6,
    "lti": 6.6,
    "total_comp": 12.3,
    "sector": "DAX",
    "year": 2024,
    "is_peer": true
  }
]
```

Pay fields are in **€ millions**; `opre` is in **€ billions**; `roa` is in **percent**.

### 8. Generate Quantile Baseline Scatterplot
Returns a dynamically generated matplotlib/seaborn visualization of the SML Quantile Regression frontier highlighting the target company.

*   **Endpoint:** `GET /api/companies/{isin}/chart.png`
*   **Query Parameters:** `year` (integer, optional)
*   **Response Headers:** `Content-Type: image/png`
*   **Example Request:**
```bash
curl -O "http://localhost:8000/api/companies/DE0007664005/chart.png"
```

### 9. Dual-Lens Chat (Activist vs Compliance Report)
Returns a tailored Dual-Lens narrative translating deterministic SML outputs into activist attacks or compliance defenses.

*   **Endpoint:** `POST /api/chat`
*   **Request Body:**
```json
{
  "company_id": "DE0007664005",
  "message": "Analyze board compensation.",
  "lens": "auditor" 
}
```
*(Note: `lens` can be "auditor" or "compliance")*
*   **Example Response:**
```json
{
  "content": "# ProxyEngine Activist Evaluation Report\n## RECOMMENDATION: VOTE AGAINST\n...\n"
}
```

### 10. Criterion Insight (Single-Lens Narrative)

Returns a lens-specific narrative for one evaluation criterion (used by the Step 3 insights panel).

*   **Endpoint:** `POST /api/insight`
*   **Request Body:**
```json
{
  "criterion": "reach",
  "lens": "auditor",
  "trace": {
    "company": "Volkswagen AG",
    "reach_ratio": 1.623,
    "multiple_of_median": 1.379,
    "ratchet_triggered": true,
    "lti_vs_salary_ratio": 3.0
  },
  "proposal": {
    "company_name": "Volkswagen AG",
    "exec_id": "Oliver Blume",
    "esg_linked": true,
    "agenda_item": "Agenda Item 6: Approval of the Remuneration System"
  }
}
```

*`criterion` values:* `reach`, `ratchet`, `mom`, `secrecy`, `ltiRatio`, `esg`

*`lens` values:* `auditor` or `compliance`

*   **Example Response:**
```json
{
  "content": "Activist Advisor Analysis: The reach ratio of 1.62x implies..."
}
```

The server applies `_filter_for_llm()` to `trace` and `proposal` before serializing into the LLM prompt.

### 11. Upload & Parse Remuneration Report
Receives a raw PDF report, parses compensation components via the Pydantic structured extraction layer, runs a stateless SML scoring pipeline, and returns the computed EvidenceTrace.

*   **Endpoint:** `POST /api/upload-pdf`
*   **Request Format:** `multipart/form-data`
*   **Form Field:** `file` (binary PDF file)
*   **Example Response:**
```json
{
  "trace": {
    "company": "Volkswagen AG",
    "isin": "DE0007664005",
    "exec_id": "Oliver Blume",
    "year": 2024,
    "cluster_id": 4,
    "opre": 322300000000.0,
    "actual_pay": 8000000.0,
    "cluster_median_pay": 5800000.0,
    "multiple_of_median": 1.379,
    "pay_premium": 1.154,
    "reach_ratio": 1.623,
    "ratchet_triggered": true,
    "secrecy_premium_flag": false,
    "lti_vs_salary_ratio": 3.0
  },
  "proposal": {
    "company_name": "Volkswagen AG",
    "exec_id": "Oliver Blume",
    "proposed_salary": 1500000.0,
    "proposed_sti": 2000000.0,
    "proposed_lti": 4500000.0,
    "esg_linked": true,
    "agenda_item": "Agenda Item 6: Approval of the Remuneration System"
  }
}
```

> **Note:** The `trace` object in upload responses is the full UI trace. Only derived fields from `TRACE_ALLOWLIST` / `PROPOSAL_ALLOWLIST` are forwarded to external LLM APIs.

---

## 5. Dual-Lens Narrative Strategy

To guarantee strict compliance and eliminate financial hallucinations, the **Dual-Lens Large Language Model (LLM)** translation layer behaves strictly as an analytical narrative compiler. It operates under two distinct system personas that swap based on the user's focus:

### Lens A: The Auditor (Activist Investor Lens)
*   **System Prompt Persona:**
    > "You are an activist institutional investor and proxy advisor (like ISS or Glass Lewis). You write direct, mathematically grounded, and ruthless voting recommendations AGAINST executive compensation proposals when they show signs of rent extraction (high Reach ratios, asymmetric ratcheting, high multiples of peer medians). Use the provided econometric evidence trace and proposal details to construct a compelling recommendation. Do not use conversational filler, get straight to the analysis and recommendation."
*   **Narrative Anchor:** Converts positive quantile regression residuals and asymmetric ratchets into aggressive proxy battle briefs advocating a **VOTE AGAINST** board approval.

### Lens B: The Defender (Corporate Board Lens)
*   **System Prompt Persona:**
    > "You are corporate secretary and legal counsel defending a corporate board's remuneration system against hostile activist shareholders. You frame statistical anomalies as strategic talent investments and ensure everything conforms to DCGK (German Corporate Governance Code) principles. Use the provided econometric evidence trace to anticipate shareholder attacks and draft the board's defensive compliance arguments."
*   **Narrative Anchor:** Reframes statistical size-premiums as international talent retention imperatives under DCGK Section G guidelines, recommending preemptive adjustments (e.g. implementing caps or clawbacks) to mitigate voting risk.

---

## 6. Testing & Mathematical Verification

To ensure regression modeling integrity and verify that ProxyEngine catches real-world governance scandals, we maintain a comprehensive test suite in `tests/`. See [`AGENTS_TESTING_GUIDE.md`](../AGENTS_TESTING_GUIDE.md) for the full test map, LLM guardrails, and execution commands.

### 1. Allianz SE (2025) — LTI Structural Imbalance
*   **Historical Ground Truth:** ISS recommended AGAINST the remuneration policy due to an excessive LTI target multiplier breaching DCGK G.1 limits.
*   **Code Verification:** `tests/test_historical_revolts.py` injects the Allianz 2025 profile (LTI = €8M, base salary = €1.8M) and asserts that the SML engine flags the LTI-vs-salary imbalance when it exceeds the 4.0x threshold.

### 2. DHL Group (2024) — Pay-for-Performance Disconnect
*   **Historical Ground Truth:** Major shareholder pushback occurred due to short-term bonus payout increases despite a contract in Return on Assets (ROA).
*   **Code Verification:** `tests/test_historical_revolts.py` injects a multi-year panel showing DHL's STI increasing while performance contracts from 7% to 4%. It asserts that the SML panel engine detects this downside insulation and successfully triggers `ratchet_triggered: True`.

---
*Created in 2026. Powered by ProxyEngine SML.*
