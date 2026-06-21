# Data directory

This folder is for **local-only** datasets. Nothing here should be committed unless it is synthetic or explicitly approved for publication.

## Default (repository / CI)

The app uses `USE_MOCK_PANEL=1` — a synthetic panel generated in code. No files in this directory are required.

## Hackathon confidential panel (local machine only)

If you have Chair-approved access to the TUM FA dataset, place derived portable extracts here **without committing them**:

- `peer_cluster_firm_years.csv`
- `peer_cluster_companies.csv`
- `peer_cluster_roster.csv`

Then run with:

```bash
export USE_MOCK_PANEL=0
export USE_CONFIDENTIAL_PANEL=1
export CONFIDENTIAL_DATA_DIR=/path/to/Chair-approved/Data   # raw ORBIS + pay files
export CONFIDENTIAL_PREDICTIONS_PATH=/path/to/local/ozkan_predictions.json  # optional
```

See [CONFIDENTIALITY.md](../CONFIDENTIALITY.md).
