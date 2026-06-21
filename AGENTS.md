# Aequitas: Executive Pay Governance (Agent Instructions)

## 🤖 IMPORTANT: System Architecture & Normalization

This file serves as the definitive source-of-truth for all AI agents, automated pipelines, and developers working in this repository. Follow these conventions strictly.

---

## 1. Core Project Structure

The project is split into a **FastAPI backend** and a **standalone custom HTML frontend**.

*   **THE REAL FRONTEND:** `/home/tanmay/Desktop/science_hack/proxyengine/src/frontend/Pay Governance Dashboard.dc.html`
    *   *Warning:* Do **NOT** edit files in `Implementation/templates/` or `Implementation/outputs/` (e.g., `index.html` or `start_portal.py`). Those are deprecated or secondary static build outputs.
*   **THE FRONTEND ENGINE:** `/home/tanmay/Desktop/science_hack/proxyengine/src/frontend/support.js`
    *   This is the custom templating engine (`DCLogic`, `sc-if`, `sc-for`) that drives frontend state and calculations.
*   **THE BACKEND SERVER:** `/home/tanmay/Desktop/science_hack/proxyengine/src/backend/main.py`
    *   This is the FastAPI application that serves the APIs and hosts the main frontend.
*   **THE SML PIPELINE ENGINE:** `/home/tanmay/Desktop/science_hack/proxyengine/src/sml_engine.py`
    *   Contains the core regression modeling (Quantile Regression, K-Means clustering, asymmetric pay-for-luck ratchets, etc.).
*   **THE DUAL-LENS AI WRAPPER:** `/home/tanmay/Desktop/science_hack/proxyengine/src/llm_wrapper.py`
    *   Coordinates the Dual-Lens AI narration (Activist Auditor Lens vs. Compliance Board Defense Lens).

---

## 2. Server Control & Execution Commands

### A. How to Start the App (Serving both Frontend & Backend)
The backend FastAPI application serves the frontend statically at `http://localhost:8000/`. Use the virtual environment Python interpreter:

```bash
# Start backend on Port 8000 (serves Pay Governance Dashboard.dc.html on '/')
/home/tanmay/Desktop/science_hack/proxyengine/venv/bin/python3 src/backend/main.py
```

### B. Virtual Environment Path
Always execute python commands, test commands, or servers using the local virtual environment interpreter:
`/home/tanmay/Desktop/science_hack/proxyengine/venv/bin/python3`

### C. Run the Regression Test Suite
Verify the integrity of the econometric mathematical models by running:
```bash
/home/tanmay/Desktop/science_hack/proxyengine/venv/bin/pytest tests/test_historical_revolts.py -v
```

---

## 3. Development Guidelines for Page 3 ("Report Page")
*   **SML Fitting vs. Local Math:** The SML regression lines should be fetched from the backend's `/api/model` and `/api/companies/{isin}/dashboard` instead of being estimated locally on the client via crude OLS.
*   **The Dual-Lens Narrative:** Leverage `/api/insight` and `/api/chat` to expose both the red-team Activist Auditor critique and the blue-team Corporate Board defense in split panels, tabs, or advisor drawers.
