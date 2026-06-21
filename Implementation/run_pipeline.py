#!/usr/bin/env python3
"""Run full pipeline and generate all step visualizations."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from pipeline import run_all
from visualize import generate_all


def main():
    print("Running executive compensation pipeline...")
    results = run_all()
    print(f"  Step 1: {results['stats']['usable_firm_years']} usable firm-years, {results['stats']['usable_firms']} firms")
    print(f"  Step 2: {results['profile']['peer_label'].nunique()} peer clusters")
    if len(results.get("ozkan_next", [])):
        print(f"  Step 3b (Ozkan): {len(results['ozkan_next'])} next-year predictions")
    print(f"  Step 8: {len(results['flags'])} firm-years in red-flag table")

    print("Generating visualizations...")
    paths = generate_all(results)
    for p in paths:
        print(f"  Saved: {p['file']}")
    print("Done.")


if __name__ == "__main__":
    main()
