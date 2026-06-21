# **DEPRECATED** Executive Compensation — Implementation

⚠️ **THIS FOLDER IS DEPRECATED.** Please use the standalone HTML dashboard (`src/frontend/Pay Governance Dashboard.dc.html`) instead.

## Quick start

```bash
cd Implementation
source .venv/bin/activate   # if not already active
python run_pipeline.py      # once: generate data + charts
python start_portal.py      # open dashboard in browser
```

**Dashboard URL:** `http://127.0.0.1:8888/` (port 8888 — safe in Chrome; avoid 5060)

## What the portal shows

1. **Predict one company** — dropdown of 130 firms → Ozkan next-year cash, LTI, total comp
2. **Peer clusters** — 7 groups with firm counts and median pay
3. **Pipeline charts** — all methodology step visualizations

## If localhost fails

| Problem | Fix |
|---------|-----|
| `ERR_UNSAFE_PORT` | Use **8888** via `start_portal.py`, not 5060 |
| Blank page in Cursor | Open URL in **Chrome or Safari** |
| `Address already in use` | Stop old server (Ctrl+C), run `start_portal.py` again |
| No companies / charts | Run `python run_pipeline.py` first |

## Output files

| File | Content |
|------|---------|
| `outputs/index.html` | Static dashboard (built by `build_portal.py`) |
| `outputs/data/peer_cluster_companies.csv` | Company ↔ cluster mapping |
| `outputs/data/ozkan_predicted_comp_next_year.csv` | All next-year predictions |
| `outputs/figures/step*.png` | Pipeline charts |

## Pipeline only (no server)

```bash
python run_pipeline.py
python build_portal.py
open outputs/index.html   # macOS — open file directly in browser
```

Note: opening `index.html` as a file works for predictions; chart images load from relative `figures/` paths.
