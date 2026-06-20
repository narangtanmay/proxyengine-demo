import sys
import os
import json
import numpy as np
import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
import matplotlib.pyplot as plt
import seaborn as sns
import io
from pydantic import BaseModel

# Ensure src directory is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sml_engine import ProxyEngineSML
from pdf_parser_poc import PDFExtractorPOC
from llm_wrapper import ProxyEngineDualLens

app = FastAPI(title="ProxyEngine API", version="1.0.0")

# Enable CORS for frontend connection (Restricted origins for security)
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000,http://localhost:5173,http://127.0.0.1:8000,http://127.0.0.1:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize engines
sml_engine = ProxyEngineSML()
cache_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "backend", "sml_cache.json")

# Fit the full pipeline so the dashboard/chart endpoints have the fitted model and
# every computed column (pay_premium, reach_ratio, cluster benchmarks, ratchets).
print("Fitting SML pipeline on the real peer-cluster panel...")
sml_engine.run_full_pipeline()
# Also load the cache so the stateless O(1) upload endpoint can score proposals.
sml_engine.load_from_cache(cache_path)

# Model-level summary (regression diagnostics + sample-wide ratchet test) is the
# same for every company, so we compute it once at startup.
MODEL_INFO = {
    "diagnostics": sml_engine.get_model_diagnostics(),
    "ratchet": sml_engine.asymmetric_ratchet_analysis(),
    "n_clusters": int(sml_engine.data["shadow_peer_cluster"].nunique()),
    "year_min": int(sml_engine.data["year"].min()),
    "year_max": int(sml_engine.data["year"].max()),
}

dual_lens_translator = ProxyEngineDualLens()

class ChatRequest(BaseModel):
    company_id: str
    message: str
    lens: str # "auditor" or "compliance"

class InsightRequest(BaseModel):
    criterion: str            # one of: reach, ratchet, mom, secrecy, ltiRatio, esg
    lens: str                 # "auditor" or "compliance"
    trace: dict               # the SML trace currently displayed
    proposal: dict | None = None  # the proposed package details (optional)

@app.get("/api/companies")
def get_companies():
    """Returns available German corporations in our dataset."""
    predictions_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ozkan_predictions.json")
    if os.path.exists(predictions_path):
        try:
            with open(predictions_path, "r") as f:
                data = json.load(f)
            return [{"id": c["isin"], "name": f"{c['name']}"} for c in data.get("companies", [])]
        except Exception:
            pass
    companies = [
        {"id": "DE0007664005", "name": "Volkswagen AG"},
        {"id": "DE000BAY0017", "name": "Bayer AG"},
        {"id": "DE0005439004", "name": "Continental AG"}
    ]
    return companies

@app.get("/api/companies/{isin}/ozkan")
def get_company_ozkan(isin: str):
    """Returns the Ozkan next-year cash, LTI, and total predictions for the firm."""
    predictions_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ozkan_predictions.json")
    if os.path.exists(predictions_path):
        try:
            with open(predictions_path, "r") as f:
                data = json.load(f)
            for c in data.get("companies", []):
                if c["isin"] == isin:
                    return c
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
    raise HTTPException(status_code=404, detail=f"Ozkan prediction not found for ISIN {isin}")

@app.get("/api/model")
def get_model_info():
    """Returns the fitted fair-pay model diagnostics and the sample-wide ratchet test.

    These values are model-level (identical for every company) and let the frontend
    render real regression statistics instead of hardcoded numbers.
    """
    return MODEL_INFO


@app.get("/api/clusters")
def get_clusters():
    """Returns the per-shadow-peer-cluster analysis (size, pay level, premium spread)."""
    return sml_engine.get_cluster_analysis().to_dict(orient="records")


@app.get("/api/treadmill")
def get_treadmill_route_b():
    """Returns the pre-calculated Oaxaca-Blinder Treadmill Route B decomposition."""
    csv_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "Implementation", "outputs", "data", "treadmill_route_b.csv"
    )
    if not os.path.exists(csv_path):
        raise HTTPException(status_code=404, detail="Oaxaca-Blinder Treadmill Route B data not found.")
    try:
        df = pd.read_csv(csv_path)
        data = df.to_dict(orient="records")[0]
        return {
            "year_first": int(data["year_first"]),
            "year_last": int(data["year_last"]),
            "delta_log_pay": float(data["delta_log_pay"]),
            "fundamentals_component": float(data["fundamentals_component"]),
            "treadmill_component": float(data["treadmill_component"]),
            "treadmill_share_pct": float(data["treadmill_share"]) * 100.0,
            "b0_beta_size": float(data["b0_beta"]),
            "bT_beta_size": float(data["bT_beta"])
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/companies/{isin}/dashboard")
def get_company_dashboard(isin: str, year: int = 2024):
    """Returns SML evidence trace metrics for the company and year."""
    try:
        trace = sml_engine.get_evidence_trace(isin, year)
        return trace
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

@app.get("/api/companies/{isin}/chart.png")
def get_company_chart(isin: str, year: int = 2024):
    """Generates the SML Quantile Regression Baseline scatterplot dynamically and returns as PNG."""
    try:
        trace = sml_engine.get_evidence_trace(isin, year)
        
        # Build plot
        fig, ax = plt.subplots(figsize=(8, 6))
        
        plot_df = sml_engine.data.copy()
        selected_cluster = trace['cluster_id']
        
        cluster_peers = plot_df[plot_df['shadow_peer_cluster'] == selected_cluster]
        other_peers = plot_df[plot_df['shadow_peer_cluster'] != selected_cluster]
        
        # Plot peers
        ax.scatter(
            np.exp(other_peers['log_size']) / 1e6, 
            np.exp(other_peers['log_pay']) / 1e6, 
            alpha=0.25, 
            color='gray', 
            label='Other Peer Panel',
            s=40
        )
        ax.scatter(
            np.exp(cluster_peers['log_size']) / 1e6, 
            np.exp(cluster_peers['log_pay']) / 1e6, 
            alpha=0.7, 
            color='#1f4287', 
            label=f'Shadow Peers (Cluster {selected_cluster})',
            s=60,
            edgecolors='black',
            linewidth=0.5
        )
        
        # Resolve the target company-year first (the fitted model needs a known year).
        comp_row = plot_df[(plot_df['isin'] == isin) & (plot_df['year'] == year)]
        if comp_row.empty:
            comp_row = plot_df[plot_df['isin'] == isin].sort_values('year', ascending=False).head(1)
        line_year = int(comp_row.iloc[0]['year'])

        # Baseline line (PDF Step 1 fair-pay line: log_pay ~ log_size + C(shadow_peer_cluster) + roa)
        sizes_range = np.linspace(cluster_peers['log_size'].min(), cluster_peers['log_size'].max(), 100)
        median_roa = cluster_peers['roa'].median()

        dummy_df = pd.DataFrame({
            'log_size': sizes_range,
            'shadow_peer_cluster': [selected_cluster] * 100,
            'roa': [median_roa] * 100
        })
        predicted_log_pays = sml_engine.model.predict(dummy_df)
        
        ax.plot(
            np.exp(sizes_range) / 1e6, 
            np.exp(predicted_log_pays) / 1e6, 
            color='#ff7600', 
            linestyle='--', 
            linewidth=2.5, 
            label='SML Quantile Baseline (q=0.5)'
        )
        
        # Current company point
        target_size = np.exp(comp_row.iloc[0]['log_size'])
        target_pay = trace['actual_pay']
        
        ax.scatter(
            target_size / 1e6, 
            target_pay / 1e6, 
            color='#ff0000', 
            edgecolors='black',
            s=150, 
            label=f"Target: {trace['company']} ({trace['year']})", 
            zorder=5
        )
        
        # Vertical residual line (expected pay on the fair-pay line at the target's size)
        target_dummy_df = pd.DataFrame({
            'log_size': [np.log(target_size)],
            'shadow_peer_cluster': [selected_cluster],
            'roa': [comp_row.iloc[0]['roa']]
        })
        expected_pay_at_target = np.exp(sml_engine.model.predict(target_dummy_df)[0])
        
        ax.vlines(
            x=target_size / 1e6,
            ymin=expected_pay_at_target / 1e6,
            ymax=target_pay / 1e6,
            colors='#ff0000',
            linestyles='solid',
            linewidth=2,
            label='Reach Residual'
        )
        
        ax.set_xscale('log')
        ax.set_yscale('log')
        ax.set_xlabel("Company Operating Revenue (Scale - € Millions, Log-Scale)", fontsize=10, fontweight='bold')
        ax.set_ylabel("Executive Total Comp (€ Millions, Log-Scale)", fontsize=10, fontweight='bold')
        ax.set_title(f"SML Quantile Frontier for {trace['company']}", fontsize=11, fontweight='bold', pad=10)
        ax.grid(True, which="both", ls="--", alpha=0.3)
        ax.legend(loc="upper left", frameon=True, facecolor='white', framealpha=0.9, fontsize=9)
        
        sns.despine()
        
        # Save to buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=150)
        buf.seek(0)
        plt.close(fig)
        
        return StreamingResponse(buf, media_type="image/png")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat")
def chat_with_translator(request: ChatRequest):
    """Returns dual-lens narrative reports based on SML trace metrics."""
    try:
        # Fetch SML trace
        trace = sml_engine.get_evidence_trace(request.company_id, 2024)
        
        # Simple proposal payload stub corresponding to the trace
        proposal_data = {
            "company_name": trace["company"],
            "exec_id": trace["exec_id"],
            "proposed_salary": trace["actual_pay"] * 0.25,
            "proposed_sti": trace["actual_pay"] * 0.30,
            "proposed_lti": trace["actual_pay"] * 0.45,
            "esg_linked": True,
            "agenda_item": "Agenda Item 6: Resolution on the Approval of the Remuneration System"
        }
        
        # User message could ask to change perspective or drill down
        # In a real system, the LLM takes this message. For our connected system,
        # we generate the selected dual-lens report and prepend the assistant's dialogue.
        if request.lens == "auditor":
            report = dual_lens_translator.generate_auditor_report(trace, proposal_data)
            intro = f"Based on your query regarding **{trace['company']}**, here is our institutional shareholder and proxy advisor report evaluating their executive compensation structure under our SML baseline.\n\n"
        else:
            report = dual_lens_translator.generate_compliance_report(trace, proposal_data)
            intro = f"In response to your inquiry about **{trace['company']}**'s Say-on-Pay audit risks, here is our corporate secretary and legal counsel defense positioning under DCGK principles.\n\n"
            
        return {"content": intro + report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/insight")
def get_criterion_insight(request: InsightRequest):
    """Returns a single-criterion, lens-specific narrative (Gemini, with deterministic fallback)."""
    try:
        proposal = request.proposal or {
            "company_name": request.trace.get("company"),
            "exec_id": request.trace.get("exec_id"),
            "proposed_salary": request.trace.get("actual_pay", 0.0) * 0.25,
            "proposed_sti": request.trace.get("actual_pay", 0.0) * 0.30,
            "proposed_lti": request.trace.get("actual_pay", 0.0) * 0.45,
            "esg_linked": True,
        }
        content = dual_lens_translator.generate_criterion_insight(
            request.criterion, request.lens, request.trace, proposal
        )
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/upload-pdf")
async def upload_remuneration_pdf(file: UploadFile = File(...)):
    """Receives and parses a PDF, then returns dynamically updated metrics."""
    try:
        file_bytes = await file.read()
        extractor = PDFExtractorPOC()
        proposal_data = extractor.process(file_bytes=file_bytes)
        
        # Stateless evaluation of the proposal in O(1) time
        trace = sml_engine.evaluate_proposal_statelessly(proposal_data)
        return {"trace": trace, "proposal": proposal_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Mount static frontend build & figures
frontend_dist_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend", "dist")
figures_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Implementation", "outputs", "figures")

from fastapi.staticfiles import StaticFiles

if os.path.exists(figures_path):
    app.mount("/figures", StaticFiles(directory=figures_path), name="figures")

if os.path.exists(frontend_dist_path):
    from fastapi.responses import FileResponse
    # We mount the API routes first, so we mount static files last as catch-all
    app.mount("/", StaticFiles(directory=frontend_dist_path, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
