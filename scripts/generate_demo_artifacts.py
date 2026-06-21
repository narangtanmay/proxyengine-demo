#!/usr/bin/env python3
"""Build NDA-safe demo artifacts (sml_cache + demo_ozkan_predictions) from the mock panel."""
from __future__ import annotations

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "src"))

os.environ["USE_MOCK_PANEL"] = "1"

from sml_engine import ProxyEngineSML  # noqa: E402


def main() -> None:
    engine = ProxyEngineSML()
    engine.run_full_pipeline()

    backend_dir = os.path.join(ROOT, "src", "backend")
    cache_path = os.path.join(backend_dir, "sml_cache.json")
    engine.save_to_cache(cache_path)
    print(f"Wrote {cache_path}")

    latest_year = int(engine.data["year"].max())
    companies = []
    for isin, grp in engine.data.groupby("isin"):
        row = grp[grp["year"] == latest_year].iloc[0]
        companies.append({
            "isin": isin,
            "name": row["company_name"],
            "peer": f"Peer_C{int(row['shadow_peer_cluster'])}",
            "index": "DEMO",
            "median_pay_k": round(float(grp["total_comp"].median()) / 1000.0, 1),
            "median_opre_m": round(float(grp["opre"].median()) / 1e6, 1),
            "pred": {},
        })

    clusters = []
    for cid, g in engine.data.groupby("shadow_peer_cluster"):
        clusters.append({
            "peer": f"Peer_C{int(cid)}",
            "n": int(g["isin"].nunique()),
            "median_pay_k": round(float(g["total_comp"].median()) / 1000.0, 1),
        })

    payload = {
        "summary": {
            "firm_years": int(len(engine.data)),
            "firms": int(engine.data["isin"].nunique()),
            "join_pct": 100.0,
            "movers": 0,
            "note": "Synthetic demo data only — not TUM FA confidential panel",
        },
        "clusters": clusters,
        "companies": companies,
    }

    demo_path = os.path.join(backend_dir, "demo_ozkan_predictions.json")
    with open(demo_path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, indent=2)
    print(f"Wrote {demo_path} ({len(companies)} companies)")


if __name__ == "__main__":
    main()
