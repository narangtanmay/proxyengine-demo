import json
import sys
import os

# Ensure local src directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sml_engine import ProxyEngineSML
from pdf_parser_poc import PDFExtractorPOC
from llm_wrapper import ProxyEngineDualLens

def run_pipeline():
    print("================================================================================")
    print("                     PROXYENGINE UNIFIED SCENARIO ANALYSIS PIPELINE                     ")
    print("================================================================================")
    
    # Step 1: SML Engine Initialization & Panel Runs
    print("\n[STEP 1] Initializing SML Econometric Engine...")
    sml_engine = ProxyEngineSML()
    print("Running end-to-end panel regressions & shadow peer clustering...")
    sml_engine.run_full_pipeline()
    print(f"Panel analysis complete. Total executive-years analyzed: {len(sml_engine.data)}")
    
    # Step 2: PDF Ingestion & Parsing
    print("\n[STEP 2] Ingesting & parsing unstructured remuneration report...")
    # Simulate processing of VW 2024 Proxy proposal
    extractor = PDFExtractorPOC()
    proposal_data = extractor.process()
    
    # Step 3: Econometric Mapping & Residual Projection
    print("\n[STEP 3] Mapping proposal data to regression baseline...")
    # In a real run, we append the proposal to the historical panel and re-run.
    # We will simulate this by evaluating the target ISIN (Volkswagen AG: DE0007664039)
    matched_isin = "DE0007664039"
    eval_year = 2024
    
    # Update panel with proposed figures dynamically
    temp_data = sml_engine.data.copy()
    temp_data = temp_data[~((temp_data['isin'] == matched_isin) & (temp_data['year'] == eval_year))]
    
    hist_row = sml_engine.data[sml_engine.data['isin'] == matched_isin].sort_values('year', ascending=False).iloc[0].copy()
    proposed_comp = proposal_data["proposed_salary"] + proposal_data["proposed_sti"] + proposal_data["proposed_lti"]
    
    new_row = hist_row.to_dict()
    new_row['year'] = eval_year
    new_row['total_comp'] = proposed_comp
    new_row['salary'] = proposal_data["proposed_salary"]
    new_row['sti'] = proposal_data["proposed_sti"]
    new_row['lti'] = proposal_data["proposed_lti"]
    
    temp_data = pd_concat_helper(temp_data, new_row)
    
    temp_engine = ProxyEngineSML(temp_data)
    temp_engine.run_full_pipeline()
    
    evidence_trace = temp_engine.get_evidence_trace(matched_isin, eval_year)
    print("Generated SML Evidence Trace:")
    print(json.dumps(evidence_trace, indent=2))
    
    # Step 4: Dual-Lens Narrative Report Generation
    print("\n[STEP 4] Activating Dual-Lens LLM Translator...")
    translator = ProxyEngineDualLens()
    
    print("\n--- [LENS 1] AUDITOR / ACTIVIST PERSPECTIVE (RECOMMENDATION) ---")
    auditor_report = translator.generate_auditor_report(evidence_trace, proposal_data)
    print(auditor_report)
    
    print("\n--- [LENS 2] COMPLIANCE / CORPORATE BOARD PERSPECTIVE (DEFENSE) ---")
    compliance_report = translator.generate_compliance_report(evidence_trace, proposal_data)
    print(compliance_report)
    print("================================================================================")

def pd_concat_helper(df, row_dict):
    import pandas as pd
    return pd.concat([df, pd.DataFrame([row_dict])], ignore_index=True)

if __name__ == "__main__":
    run_pipeline()
