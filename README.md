# Aequitas / ProxyEngine (public demo)

AI-powered executive compensation benchmarking and governance red-flag detection — built for the **TUM Science Hackathon** (Chair of Financial Accounting).

**Public demo repository:** [github.com/narangtanmay/proxyengine-demo](https://github.com/narangtanmay/proxyengine-demo) — synthetic data only; no confidential hackathon panel is included or has ever been committed here.

## Important: confidentiality

This repository runs on **synthetic demo data by default**. The real German executive compensation panel provided under the hackathon NDA must stay on your local machine only. See [CONFIDENTIALITY.md](CONFIDENTIALITY.md).

## Quick start

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # optional: DEEPSEEK_API_KEY for LLM features

python scripts/generate_demo_artifacts.py   # refresh demo cache if needed
python src/backend/main.py                  # http://localhost:8000/
```

## Architecture

| Component | Path |
|-----------|------|
| Dashboard | `src/frontend/Pay Governance Dashboard.dc.html` |
| Frontend engine | `src/frontend/support.js` |
| API | `src/backend/main.py` |
| SML pipeline | `src/sml_engine.py` |
| Dual-lens LLM | `src/llm_wrapper.py` |

Full design: [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md)

## Tests

```bash
pytest tests/ -v
```

## Environment variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `USE_MOCK_PANEL` | `1` | Synthetic demo panel (NDA-safe) |
| `CONFIDENTIAL_DATA_DIR` | — | Local path to Chair-approved raw data |
| `USE_CONFIDENTIAL_PANEL` | — | Set `1` with above to load real panel locally |
| `CONFIDENTIAL_PREDICTIONS_PATH` | — | Optional local company metadata JSON |
| `DEEPSEEK_API_KEY` | — | External LLM (filtered payloads only) |
