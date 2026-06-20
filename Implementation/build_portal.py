#!/usr/bin/env python3
"""Build a static dashboard (works without Flask)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "outputs" / "data"
FIGURES = ROOT / "outputs" / "figures"
OUT = ROOT / "outputs" / "index.html"


def _read_csv(name: str) -> pd.DataFrame:
    path = DATA / name
    return pd.read_csv(path) if path.exists() else pd.DataFrame()


def build() -> Path:
    stats = _read_csv("step1_stats.csv")
    peers = _read_csv("peer_cluster_companies.csv")
    preds = _read_csv("ozkan_predicted_comp_next_year.csv")
    figures = _read_csv("figure_index.csv")

    summary = {}
    if len(stats):
        row = stats.iloc[0]
        summary = {
            "firm_years": int(row.get("usable_firm_years", 0)),
            "firms": int(row.get("usable_firms", 0)),
            "join_pct": round(float(row.get("join_rate", 0)) * 100, 1),
            "movers": int(row.get("movers", 0)),
        }

    cluster_rows = []
    if len(peers):
        grp = peers.groupby("peer_label").agg(
            n=("isin", "count"), median_pay=("median_pay", "median")
        ).reset_index()
        for r in grp.to_dict("records"):
            cluster_rows.append({
                "peer": r["peer_label"],
                "n": int(r["n"]),
                "median_pay_k": round(float(r["median_pay"]), 0),
            })

    pred_map = {}
    if len(preds):
        for r in preds.to_dict("records"):
            pred_map[r["isin"]] = {
                "company": r["company_shortname"],
                "peer": r["peer_label"],
                "fund_year": int(r.get("fundamental_year", 0)),
                "pred_year": int(r.get("prediction_year", 0)),
                "cash_k": round(float(r.get("cash", 0)), 0),
                "lti_k": round(float(r.get("lti", 0)), 0),
                "total_k": round(float(r.get("predicted_total_comp", 0)), 0),
            }

    companies = []
    if len(peers):
        for r in peers.sort_values("company_shortname").to_dict("records"):
            p = pred_map.get(r["isin"], {})
            companies.append({
                "isin": r["isin"],
                "name": r["company_shortname"],
                "peer": r.get("peer_label", ""),
                "index": r.get("index_listing") or "—",
                "median_pay_k": round(float(r.get("median_pay", 0)), 0),
                "median_opre_m": round(float(r.get("median_opre", 0)) / 1e6, 0),
                "pred": p,
            })

    chart_rows = []
    if len(figures):
        for r in figures.to_dict("records"):
            f = r.get("file", "")
            if (FIGURES / f).exists():
                chart_rows.append({
                    "step": int(r["step"]),
                    "title": r.get("title", f),
                    "file": f,
                })

    payload = json.dumps({
        "summary": summary,
        "clusters": cluster_rows,
        "companies": companies,
        "charts": chart_rows,
    })

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Executive Compensation Dashboard</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:system-ui,-apple-system,sans-serif;background:#f4f6f9;color:#1a2332;line-height:1.6}}
.wrap{{max-width:1100px;margin:0 auto;padding:0 1.25rem 3rem}}
.hero{{background:linear-gradient(135deg,#dbeafe,#f4f6f9);padding:2.5rem 0;border-bottom:1px solid #d8dee9}}
.hero h1{{font-size:1.85rem;margin:.4rem 0}}
.sub{{color:#5c6b7f}}
.stats{{display:flex;gap:1.5rem;flex-wrap:wrap;margin-top:1.25rem}}
.stats div{{background:#fff;border:1px solid #d8dee9;border-radius:8px;padding:.75rem 1rem;min-width:100px}}
.stats strong{{display:block;font-size:1.4rem;color:#2563eb}}
.nav{{display:flex;gap:.5rem;flex-wrap:wrap;padding:1.25rem 0}}
.nav a{{padding:.45rem .9rem;background:#2563eb;color:#fff;text-decoration:none;border-radius:6px;font-weight:600;font-size:.9rem}}
.nav a.green{{background:#16a34a}}
.card{{background:#fff;border:1px solid #d8dee9;border-radius:10px;padding:1.25rem;margin-bottom:1.25rem;box-shadow:0 1px 3px rgba(0,0,0,.06)}}
.card h2{{font-size:1.2rem;margin-bottom:.5rem}}
.badge{{display:inline-block;background:#2563eb;color:#fff;font-size:.7rem;font-weight:700;padding:.2rem .55rem;border-radius:4px;margin-bottom:.5rem}}
label{{display:block;font-weight:600;margin-bottom:.4rem}}
select,button{{font-size:1rem;padding:.6rem .85rem;border-radius:8px;border:1px solid #d8dee9}}
select{{width:100%;max-width:480px;margin-bottom:.75rem}}
button{{background:#2563eb;color:#fff;border:none;font-weight:600;cursor:pointer}}
button:hover{{background:#1d4ed8}}
table{{width:100%;border-collapse:collapse;font-size:.9rem}}
th,td{{padding:.55rem .75rem;border-bottom:1px solid #d8dee9;text-align:left}}
th{{background:#eef2f7}}
.meta{{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:.6rem;margin:1rem 0}}
.meta div{{background:#f8fafc;border:1px solid #d8dee9;border-radius:8px;padding:.55rem .75rem}}
.meta small{{display:block;color:#5c6b7f;font-size:.7rem;text-transform:uppercase}}
.meta span{{font-weight:700}}
.total{{font-size:1.5rem;color:#2563eb;font-weight:800}}
img{{width:100%;height:auto;display:block;border-radius:6px;border:1px solid #d8dee9}}
.warn{{background:#fef3c7;border:1px dashed #f59e0b;padding:1rem;border-radius:8px;color:#92400e}}
.hidden{{display:none}}
footer{{color:#5c6b7f;font-size:.85rem;padding-top:1.5rem;border-top:1px solid #d8dee9;margin-top:1rem}}
</style>
</head>
<body>
<header class="hero"><div class="wrap">
  <small style="color:#2563eb;font-weight:700;text-transform:uppercase;letter-spacing:.1em">TUM Science Hackathon</small>
  <h1>Executive Compensation Dashboard</h1>
  <p class="sub">Peer clustering · Ozkan (2011) prediction · Methodology pipeline</p>
  <div class="stats" id="stats"></div>
</div></header>

<main class="wrap">
  <nav class="nav">
    <a href="#predict" class="green">Predict Company</a>
    <a href="#clusters">Clusters</a>
    <a href="#charts">Charts</a>
  </nav>

  <section id="predict" class="card">
    <span class="badge">Step 1 — Choose company</span>
    <h2>Predict next-year total compensation</h2>
    <p class="sub" style="margin-bottom:1rem">Select one of 130 companies. Ozkan Eq. 6.1 model within peer cluster.</p>
    <label for="co">Which company?</label>
    <select id="co"><option value="">— Choose a company —</option></select>
    <button type="button" id="go">Predict compensation</button>
    <div id="result" class="hidden" style="margin-top:1.25rem"></div>
  </section>

  <section id="clusters" class="card">
    <span class="badge">Peer clusters</span>
    <h2>7 benchmark groups (130 firms)</h2>
    <div style="overflow-x:auto"><table id="cluster-table"><thead><tr><th>Cluster</th><th>Firms</th><th>Median pay €k</th></tr></thead><tbody></tbody></table></div>
  </section>

  <section id="charts" class="card">
    <span class="badge">Pipeline</span>
    <h2>Methodology charts</h2>
    <div id="charts-list"></div>
  </section>

  <footer><p>Run <code>python start_portal.py</code> from Implementation folder · Data in <code>outputs/data/</code></p></footer>
</main>

<script>
const DATA = {payload};

function init() {{
  const s = DATA.summary;
  if (s.firm_years) {{
    document.getElementById('stats').innerHTML = [
      ['Firm-years', s.firm_years], ['Firms', s.firms],
      ['ORBIS join', s.join_pct + '%'], ['Movers', s.movers]
    ].map(([l,v]) => `<div><strong>${{v}}</strong>${{l}}</div>`).join('');
  }}
  const tb = document.querySelector('#cluster-table tbody');
  DATA.clusters.forEach(c => {{
    tb.innerHTML += `<tr><td>${{c.peer}}</td><td>${{c.n}}</td><td>${{c.median_pay_k}}</td></tr>`;
  }});
  const sel = document.getElementById('co');
  DATA.companies.forEach(c => {{
    sel.innerHTML += `<option value="${{c.isin}}">${{c.name}} (${{c.peer}})</option>`;
  }});
  const cl = document.getElementById('charts-list');
  DATA.charts.forEach(ch => {{
    cl.innerHTML += `<div style="margin-bottom:1.5rem"><h3 style="margin-bottom:.5rem">${{ch.title}}</h3><img src="figures/${{ch.file}}" alt="${{ch.title}}"></div>`;
  }});
}}

function predict() {{
  const isin = document.getElementById('co').value;
  const box = document.getElementById('result');
  if (!isin) {{ alert('Please choose a company first.'); return; }}
  const c = DATA.companies.find(x => x.isin === isin);
  if (!c || !c.pred || !c.pred.total_k) {{
    box.className = 'warn'; box.innerHTML = 'No prediction for this company. Run <code>python run_pipeline.py</code> first.';
    return;
  }}
  const p = c.pred;
  box.className = '';
  box.innerHTML = `
    <h3 style="margin-bottom:.5rem">${{c.name}}</h3>
    <div class="meta">
      <div><small>Peer cluster</small><span>${{c.peer}}</span></div>
      <div><small>Index</small><span>${{c.index}}</span></div>
      <div><small>Fundamentals from</small><span>${{p.fund_year}}</span></div>
      <div><small>Predicting year</small><span>${{p.pred_year}}</span></div>
      <div><small>Peer median pay</small><span>${{c.median_pay_k}} €k</span></div>
    </div>
    <table>
      <thead><tr><th>Component</th><th>Predicted (€k)</th></tr></thead>
      <tbody>
        <tr><td>Cash (salary + STI)</td><td><strong>${{p.cash_k}}</strong></td></tr>
        <tr><td>LTI</td><td><strong>${{p.lti_k}}</strong></td></tr>
        <tr style="background:#eff6ff"><td><strong>Total direct comp</strong></td><td class="total">${{p.total_k}} €k</td></tr>
      </tbody>
    </table>
    <p class="sub" style="margin-top:.75rem">Ozkan (2011) Eq. 6.1 · real 2015 euros, thousands</p>`;
}}

document.getElementById('go').addEventListener('click', predict);
document.getElementById('co').addEventListener('change', predict);
init();
</script>
</body>
</html>"""

    OUT.write_text(html, encoding="utf-8")
    print(f"Built portal: {OUT}")
    print(f"  Companies: {len(companies)}  Charts: {len(chart_rows)}")
    return OUT


if __name__ == "__main__":
    if not (DATA / "peer_cluster_companies.csv").exists():
        print("Missing pipeline outputs. Run: python run_pipeline.py")
        sys.exit(1)
    build()
