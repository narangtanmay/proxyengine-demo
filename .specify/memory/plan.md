# ProxyEngine Implementation Plan

## 1. Technical Approach
We will build the ProxyEngine as a Python-based backend application with a lightweight UI.
- **Backend:** FastAPI for API orchestration.
- **Data/SML Engine:** Pandas, Scikit-Learn (K-Means), Statsmodels (Quantile Regression).
- **LLM Integration:** OpenAI/Claude API for parsing PDFs (in POC mode) and generating narrative reports.
- **Frontend:** Streamlit or a basic React app (Streamlit preferred for fast hackathon turnaround).

## 2. Implementation Phases

### Phase 1: Core SML Engine (Backend)
1. Ingest dummy DAX panel data to simulate the ORBIS format.
2. Implement K-Means clustering for Shadow Peers.
3. Implement Lasso-Regularized Quantile Regression to calculate the Reach ratio.
4. Implement Asymmetric Ratchet detection.
5. Export results as an `EvidenceTrace` JSON.

### Phase 2: PDF Parsing POC (Input Layer)
1. Build `pdf_parser_poc.py` to ingest a PDF.
2. Mock the extraction of `salary`, `sti`, `lti` using Pydantic schemas.

### Phase 3: LLM Dual-Lens Wrapper (Output Layer)
1. Build the translation scripts that take the `EvidenceTrace` JSON.
2. Implement prompts for the **Auditor Mode** and **Compliance Mode**.

### Phase 4: UI Dashboard Integration
1. Scaffold a Streamlit dashboard.
2. Integrate the PDF upload button.
3. Implement the Dual-Lens Toggle.
4. Visualize the Reach scatterplot and display the LLM output.

## 3. Risks & Mitigations
- **Overfitting Risk:** Prevented by using constrained Quantile Regression ($\beta \approx 0.3$) and limiting features.
- **LLM Hallucinations:** Prevented by strictly constraining the LLM context window to the EvidenceTrace JSON.
- **Data Join Complexity:** Prevented by validating the math on 3-5 hand-picked DAX companies before attempting to join all 3,750 executive-years.
