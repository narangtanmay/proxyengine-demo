# PayAudit: Executive Pay Governance (Claude/Agent Guide)

## 🤖 System Architecture & Conventions

This file defines the codebase environment and development standards for Claude and other AI agents.

---

## 1. Commands

*   **Run Server:** `/home/tanmay/Desktop/science_hack/proxyengine/venv/bin/python3 src/backend/main.py`
    *   *Port:* 8000
    *   *URLs:* Dashboard at `http://localhost:8000/`, API endpoints at `http://localhost:8000/api/...`
*   **Run Tests:** `/home/tanmay/Desktop/science_hack/proxyengine/venv/bin/pytest tests/test_historical_revolts.py -v`

---

## 2. Core Project Map

*   **The Main Frontend Template:** `src/frontend/Pay Governance Dashboard.dc.html`
*   **The Frontend Logic Engine:** `src/frontend/support.js`
*   **The Backend FastAPI App:** `src/backend/main.py`
*   **The SML Econometric Pipeline:** `src/sml_engine.py`
*   **The Dual-Lens Narrative Wrapper:** `src/llm_wrapper.py`

*Note: Never modify files in `Implementation/templates/` or `Implementation/outputs/` as they are deprecated or secondary static build folders.*

---

## 3. Development Guidelines

*   **Python Interpreter:** Always use the virtualenv Python at `/home/tanmay/Desktop/science_hack/proxyengine/venv/bin/python3`.
*   **Page 3 (Automated Report):** All econometric regression curves and metrics must be driven by backend endpoints (`/api/model` and `/api/companies/{isin}/dashboard`) rather than being calculated locally on the client.
*   **Narrative Lenses:** Provide both the Activist Auditor (Critique) and Compliance Board (Defense) viewpoints to present a balanced boardroom simulator.
