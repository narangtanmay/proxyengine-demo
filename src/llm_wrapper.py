import os
import json
from typing import Dict, Any
from dotenv import load_dotenv

load_dotenv()

class ProxyEngineDualLens:
    def __init__(self):
        """
        Dual-Lens LLM Translator.
        Takes deterministic econometric flags from the SML pipeline (EvidenceTrace)
        and translates them into either an activist shareholder attack (Auditor Lens)
        or a board compliance defense (Corporate Board Lens).
        """
        pass

    def _generate_narrative_with_api(self, mode: str, trace: Dict[str, Any], proposal_data: Dict[str, Any]) -> str:
        """
        Uses OpenAI or Anthropic API to generate tailored narrative reports if credentials exist.
        """
        openai_key = os.getenv("OPENAI_API_KEY")
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        
        system_prompts = {
            "auditor": (
                "You are an activist institutional investor and proxy advisor (like ISS or Glass Lewis). "
                "You write direct, mathematically grounded, and ruthless voting recommendations AGAINST executive compensation proposals "
                "when they show signs of rent extraction (high Reach ratios, asymmetric ratcheting, high multiples of peer medians). "
                "Use the provided econometric evidence trace and proposal details to construct a compelling recommendation. "
                "Do not use conversational filler, get straight to the analysis and recommendation."
            ),
            "compliance": (
                "You are corporate secretary and legal counsel defending a corporate board's remuneration system "
                "against hostile activist shareholders. You frame statistical anomalies as strategic talent investments "
                "and ensure everything conforms to DCGK (German Corporate Governance Code) principles. "
                "Use the provided econometric evidence trace to anticipate shareholder attacks and draft the board's defensive compliance arguments."
            )
        }
        
        user_content = (
            f"Econometric Evidence Trace (SML Output):\n"
            f"{json.dumps(trace, indent=2)}\n\n"
            f"Remuneration Proposal Details (PDF Parser Output):\n"
            f"{json.dumps(proposal_data, indent=2)}"
        )
        
        # Try OpenAI
        if openai_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=openai_key)
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompts[mode]},
                        {"role": "user", "content": user_content}
                    ],
                    temperature=0.2,
                    max_tokens=1500
                )
                return response.choices[0].message.content
            except Exception as e:
                print(f"[LLM Dual-Lens] OpenAI call failed: {e}. Falling back to template generator.")
                
        # Try Anthropic
        elif anthropic_key:
            try:
                import anthropic
                client = anthropic.Anthropic(api_key=anthropic_key)
                response = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1500,
                    system=system_prompts[mode],
                    messages=[{"role": "user", "content": user_content}],
                    temperature=0.2
                )
                return response.content[0].text
            except Exception as e:
                print(f"[LLM Dual-Lens] Anthropic call failed: {e}. Falling back to template generator.")
                
        return ""

    def generate_auditor_report(self, trace: Dict[str, Any], proposal_data: Dict[str, Any]) -> str:
        """
        Generates the Activist Investor / Proxy Advisor audit report (VOTE AGAINST).
        """
        # Try API first
        api_report = self._generate_narrative_with_api("auditor", trace, proposal_data)
        if api_report:
            return api_report
            
        # Fallback to deterministic high-fidelity templates
        company = trace.get("company", proposal_data.get("company_name", "the Company"))
        exec_id = trace.get("exec_id", proposal_data.get("exec_id", "the CEO"))
        agenda_item = proposal_data.get("agenda_item", "Approval of Remuneration System")
        reach_ratio = trace.get("reach_ratio", 1.0)
        ratchet_triggered = trace.get("ratchet_triggered", False)
        secrecy_premium = trace.get("secrecy_premium_flag", False)
        lti_vs_salary_ratio = trace.get("lti_vs_salary_ratio", proposal_data.get("proposed_lti", 0.0) / proposal_data.get("proposed_salary", 1.0))
        cluster_id = trace.get("cluster_id", 0)
        actual_pay = trace.get("actual_pay", proposal_data.get("proposed_salary", 0.0) * 3)
        cluster_median_pay = trace.get("cluster_median_pay", actual_pay / 1.5)
        multiple_of_median = trace.get("multiple_of_median", actual_pay / cluster_median_pay)
        
        # Sub-texts based on flags
        if ratchet_triggered:
            ratchet_text = (
                f"SML panel regression detected a highly egregious **Asymmetric Ratchet (Pay-for-Luck)**. "
                f"During the recent fiscal period, {exec_id}'s total compensation was increased even though "
                f"firm ROA contracted. This violates the pay-for-performance principle."
            )
        else:
            ratchet_text = "No systemic asymmetric ratcheting was flagged in the 3-year panel; however, the absolute compensation level remains unaligned."
            
        if secrecy_premium:
            secrecy_text = (
                f"The executive has actively opted out of individual compensation disclosure provisions under § 286 Abs. 5 HGB. "
                f"A 'Secrecy Premium Flag' is active, raising governance concerns about transparency and accountability."
            )
        else:
            secrecy_text = "Compensation disclosure complies with standard publication guidelines under German commercial law."
            
        report = f"""# ProxyEngine Activist Evaluation Report
## RECOMMENDATION: VOTE AGAINST 
### Agenda Item: {agenda_item}

### Executive Summary
We recommend that institutional shareholders vote **AGAINST** the proposed remuneration system for the Executive Board of **{company}**. 

1. **Egregious 'Reach' Anomaly:** SML Quantile Regression analysis indicates that chief executive **{exec_id}** is compensated as if running a company **{reach_ratio:.1f}x** the size of **{company}**'s actual economic scale, indicating substantial unearned rent extraction.
2. **Asymmetric Downside Protection:** {ratchet_text}
3. **Imbalanced Compensation Structure:** The proposed Long-Term Incentive (LTI) is **{lti_vs_salary_ratio:.2f}x** the base fixed salary. While equity linkage is theoretically alignment-positive, here it is leveraged on top of an inflated size premium.
4. **Transparency and Disclosure:** {secrecy_text}

### Econometric Evidence & Metrics
* **Shadow Peer Universe:** Cluster {cluster_id} (Grouped by Asset Turnover, ROA, and Gearing).
* **Multiple of Median (MoM):** **{multiple_of_median:.2f}x** the cluster median pay (exceeding ISS high-concern threshold of 1.5x).
* **Proposed Target Pay:** €{actual_pay:,.2f} vs Peer Median €{cluster_median_pay:,.2f}

**Conclusion:** This package represents a Transfer of Wealth from shareholders to the Executive Board without corresponding downside risk. We urge institutional clients to vote **AGAINST**."""
        return report

    def generate_compliance_report(self, trace: Dict[str, Any], proposal_data: Dict[str, Any]) -> str:
        """
        Generates the Corporate Board / Defense report.
        """
        # Try API first
        api_report = self._generate_narrative_with_api("compliance", trace, proposal_data)
        if api_report:
            return api_report
            
        # Fallback to deterministic high-fidelity templates
        company = trace.get("company", proposal_data.get("company_name", "the Company"))
        exec_id = trace.get("exec_id", proposal_data.get("exec_id", "the CEO"))
        agenda_item = proposal_data.get("agenda_item", "Approval of Remuneration System")
        reach_ratio = trace.get("reach_ratio", 1.0)
        ratchet_triggered = trace.get("ratchet_triggered", False)
        secrecy_premium = trace.get("secrecy_premium_flag", False)
        lti_vs_salary_ratio = trace.get("lti_vs_salary_ratio", proposal_data.get("proposed_lti", 0.0) / proposal_data.get("proposed_salary", 1.0))
        cluster_id = trace.get("cluster_id", 0)
        actual_pay = trace.get("actual_pay", proposal_data.get("proposed_salary", 0.0) * 3)
        cluster_median_pay = trace.get("cluster_median_pay", actual_pay / 1.5)
        multiple_of_median = trace.get("multiple_of_median", actual_pay / cluster_median_pay)
        
        esg_linked = proposal_data.get("esg_linked", False)
        if esg_linked:
            esg_text = "explicit inclusion of ESG-linked KPIs in the STI/LTI performance scorecards to align with DCGK section G.1"
        else:
            esg_text = "urgent necessity to introduce ESG/Sustainability targets to mitigate criticisms over pure cash performance criteria"

        report = f"""# ProxyEngine Corporate Board Compliance Report
## STATUS: HIGH RISK (Say-on-Pay Rejection Risk detected)
### Agenda Item: {agenda_item}

### Strategic Board Action Required
The remuneration proposal for **{company}**'s Executive Board is highly likely to trigger negative voting recommendations from major proxy advisors (such as ISS and Glass Lewis) due to high statistical pay anomalies. The board must prepare its defensive positioning and DCGK compliance arguments immediately.

### Econometric Vulnerabilities & Board Counter-Arguments

1. **The 'Reach' Anomaly ({reach_ratio:.1f}x size premium):**
   * *The Threat:* Proxy advisors will flag that CEO **{exec_id}** is paid like a firm **{reach_ratio:.1f}x** larger than **{company}**.
   * *Board Defense (DCGK G.2 / G.9):* The board must release disclosures justifying this premium as a contractual retention necessity in an internationally competitive CEO marketplace. Cite that **{company}**'s global operations, regulatory complexities, and cross-border footprint match the scale of the international "Shadow Peers" in Cluster {cluster_id}.

2. **Asymmetric Ratcheting Flag (Pay-for-Luck):**
   * *The Threat:* Econometric panel regression triggered an Asymmetric Ratchet flag. Pay increased during a period of ROA contraction.
   * *Board Defense (DCGK G.10):* The board must release disclosures explaining that the recent compensation adjustment was driven by the completion of highly complex long-term strategic transformation milestones (rather than cyclical financial ROA), and highlight the **{esg_text}**.

3. **LTI-to-Salary Ratio ({lti_vs_salary_ratio:.2f}x):**
   * *The Threat:* Extreme long-term equity-incentive tilt.
   * *Board Defense (DCGK G.1):* Frame this tilt as a deliberate governance decision to align the vast majority of CEO compensation directly with long-term shareholder return (TSR), ensuring that {exec_id} is only rewarded if shareholders win.

### Action Plan for Board Communication
* **Preemptive Disclosure:** Draft a supplementary corporate governance statement detailing the global peer comparison methodology used by the supervisory board.
* **Shareholder Outreach:** Schedule 1-on-1 engagement calls with top 10 institutional shareholders to proactively explain the size premium and contract conditions.
* **Governance Review:** Integrate the proposed {esg_text} to satisfy ISS sustainability alignment checks."""
        return report

if __name__ == "__main__":
    # Test
    dual_lens = ProxyEngineDualLens()
    trace = {
        "company": "Volkswagen AG",
        "exec_id": "Oliver Blume",
        "cluster_id": 1,
        "actual_pay": 8000000.0,
        "cluster_median_pay": 4500000.0,
        "multiple_of_median": 1.78,
        "reach_ratio": 2.4,
        "ratchet_triggered": True,
        "secrecy_premium_flag": False,
        "lti_vs_salary_ratio": 3.0
    }
    proposal = {
        "company_name": "Volkswagen AG",
        "exec_id": "Oliver Blume",
        "proposed_salary": 1500000.0,
        "proposed_sti": 2000000.0,
        "proposed_lti": 4500000.0,
        "esg_linked": True,
        "agenda_item": "Agenda Item 6: Approval of the Remuneration System"
    }
    
    print("\n=== AUDITOR REPORT ===\n")
    print(dual_lens.generate_auditor_report(trace, proposal))
    print("\n=== COMPLIANCE REPORT ===\n")
    print(dual_lens.generate_compliance_report(trace, proposal))
