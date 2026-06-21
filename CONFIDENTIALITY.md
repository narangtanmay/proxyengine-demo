# Confidentiality and Data Use (TUM Science Hackathon NDA)

This repository implements the **TUM Science Hackathon** challenge *AI-Powered Executive Compensation Benchmarking and Red Flag Detection* for the Chair of Financial Accounting (Prof. Dr. Jürgen Ernstberger).

## What this repo contains

- **Application code only** — SML engine, FastAPI backend, dashboard, dual-lens LLM wrapper.
- **Synthetic demo data** — `USE_MOCK_PANEL=1` (default) generates fictional firm-year panels for local demos and CI.
- **No confidential dataset** — the ~15-year German executive compensation panel provided under NDA is **not** included and must not be committed.

## NDA alignment

| NDA requirement | Implementation |
|-----------------|----------------|
| Do not publish confidential data or Project Results without Chair consent | Repo ships mock data only; real panel loaded only via local env vars |
| Do not upload confidential data to public LLMs / external repos | `llm_wrapper.py` allowlists abstract ratios/flags; raw pay and ISINs are stripped before API calls |
| Do not share dataset with third parties | `data/peer_cluster_*.csv`, ORBIS extracts, and `ozkan_predictions.json` are gitignored |
| IP vests with the Chair | See hackathon NDA §7; this public repo is a **sanitized demo fork** for portfolio use only after Chair approval |

## Running with Chair-approved local data (hackathon only)

Never commit files from this workflow:

```bash
export CONFIDENTIAL_DATA_DIR="/path/to/Chair-approved/Data"
export USE_MOCK_PANEL=0
export USE_CONFIDENTIAL_PANEL=1
# optional: export CONFIDENTIAL_PREDICTIONS_PATH="/path/to/local/ozkan_predictions.json"
python src/backend/main.py
```

## External AI services

Set `DEEPSEEK_API_KEY` only for **public remuneration PDFs** and **filtered trace summaries**. Do not paste raw panel rows, ORBIS fields, or identifiable compensation amounts into prompts.

## Contact

For publication, GitHub visibility, or reuse of Project Results, obtain **prior written consent** from the Chair of Financial Accounting, TUM School of Management.
