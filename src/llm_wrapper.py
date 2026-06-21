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

    # Fields safe to send to a third-party LLM API: abstract, derived ratios/flags only.
    # Raw proprietary figures (opre, actual_pay, isin, _traceability_map) and raw proposed
    # dollar amounts (proposed_salary, proposed_sti, proposed_lti) must never leave this process.
    TRACE_ALLOWLIST = {
        "company", "exec_id", "year", "cluster_id", "multiple_of_median",
        "pay_premium", "reach_ratio", "ratchet_triggered", "secrecy_premium_flag",
        "lti_vs_salary_ratio", "roa", "gear", "sector", "salary_benchmark",
        "sti_benchmark", "lti_benchmark", "hidden_stretch", "hidden_stretch_variance",
        "internal_concentration_ratio", "concentration_ratchet_triggered",
    }
    PROPOSAL_ALLOWLIST = {"company_name", "exec_id", "esg_linked", "agenda_item"}

    @staticmethod
    def _filter_for_llm(trace: Dict[str, Any], proposal_data: Dict[str, Any]) -> tuple:
        """Strip raw proprietary fields before any data is serialized into an LLM prompt."""
        filtered_trace = {k: v for k, v in trace.items() if k in ProxyEngineDualLens.TRACE_ALLOWLIST}
        filtered_proposal = {k: v for k, v in proposal_data.items() if k in ProxyEngineDualLens.PROPOSAL_ALLOWLIST}
        return filtered_trace, filtered_proposal

    def _generate_narrative_with_api(self, mode: str, trace: Dict[str, Any], proposal_data: Dict[str, Any], user_query: str = None) -> str:
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
        
        system_prompt = system_prompts[mode]
        if user_query:
            if mode == "auditor":
                system_prompt += (
                    f"\n\nAn investor has queried: \"{user_query}\". "
                    "You MUST tailor your response to directly answer this question, grounding all arguments "
                    "strictly in the SML Evidence Trace."
                )
            else:
                system_prompt += (
                    f"\n\nThe board/counsel has queried: \"{user_query}\". "
                    "You MUST tailor your response to directly answer this question, grounding all arguments "
                    "strictly in the SML Evidence Trace and DCGK guidelines."
                )
        
        filtered_trace, filtered_proposal = self._filter_for_llm(trace, proposal_data)
        user_content = (
            f"Econometric Evidence Trace (SML Output):\n"
            f"{json.dumps(filtered_trace, indent=2)}\n\n"
            f"Remuneration Proposal Details (PDF Parser Output):\n"
            f"{json.dumps(filtered_proposal, indent=2)}"
        )
        
        # Try OpenAI
        if openai_key:
            try:
                from openai import OpenAI
                client = OpenAI(api_key=openai_key)
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
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
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_content}],
                    temperature=0.2
                )
                return response.content[0].text
            except Exception as e:
                print(f"[LLM Dual-Lens] Anthropic call failed: {e}. Falling back to template generator.")

        return ""

    # ------------------------------------------------------------------ #
    # Per-criterion AI insights (Gemini)                                 #
    # ------------------------------------------------------------------ #

    # One short, lens-neutral description of what each checklist criterion is asking,
    # plus which deterministic SML trace fields ground the answer (no hallucinated numbers).
    CRITERION_GUIDE = {
        "reach": (
            "the econometric 'Reach' anomaly - the size-equivalent restatement of the pay premium, "
            "reach = exp(residual / beta). Grounding fields: reach_ratio, pay_premium, opre."
        ),
        "ratchet": (
            "asymmetric ratcheting / 'pay-for-luck' - whether total pay rose while firm profitability (ROA) "
            "contracted year-over-year. Grounding field: ratchet_triggered."
        ),
        "mom": (
            "the ISS Multiple-of-Median check - proposed total pay divided by the shadow-peer cluster median. "
            "The ISS high-concern threshold is 1.5x. Grounding fields: multiple_of_median, cluster_median_pay, actual_pay."
        ),
        "secrecy": (
            "the secrecy premium - whether the board opted out of individual pay disclosure under section 286 Abs. 5 HGB. "
            "Grounding field: secrecy_premium_flag."
        ),
        "ltiRatio": (
            "the Long-Term-Incentive to fixed-base-salary balance under DCGK Section G.1; the imbalance threshold is ~4.0x. "
            "Grounding fields: lti_vs_salary_ratio, proposed_lti, proposed_salary."
        ),
        "esg": (
            "whether variable remuneration is anchored to quantifiable ESG / sustainability KPIs under DCGK Section G.1. "
            "Grounding field: esg_linked."
        ),
        "stretch": (
            "the hidden stretch / component divergence anomaly - showing whether excessive pay is masked inside complex, "
            "divergent variable components. Grounding fields: hidden_stretch, hidden_stretch_variance."
        ),
        "concentration": (
            "the executive board internal concentration ratio C_jt - dividing CEO pay by the median other-board-member pay, "
            "and showing whether concentration ratcheted upward over time. Grounding fields: internal_concentration_ratio, concentration_ratchet_triggered."
        ),
    }

    SYSTEM_PROMPTS = {
        "auditor": (
            "You are an activist institutional investor and proxy advisor (in the mould of ISS or Glass Lewis). "
            "You write a direct, mathematically grounded, and ruthless analysis of ONE specific compensation finding, "
            "building toward a VOTE AGAINST when the evidence shows rent extraction. "
            "Open with the prefix '🔍 Activist Advisor Analysis:'. "
            "Use ONLY the numbers provided in the evidence trace - never invent figures. "
            "Keep it to 2-4 sentences, no headings, no bullet lists, no conversational filler."
        ),
        "compliance": (
            "You are corporate secretary and legal counsel defending a German supervisory board's remuneration system "
            "against hostile activist shareholders. You frame ONE specific statistical finding as a defensible, "
            "strategically justified decision compliant with the DCGK (German Corporate Governance Code). "
            "Open with the prefix '🛡️ Corporate Board Counsel Defense:'. "
            "Use ONLY the numbers provided in the evidence trace - never invent figures. "
            "Keep it to 2-4 sentences, no headings, no bullet lists, no conversational filler."
        ),
    }

    def _build_insight_user_content(self, criterion: str, trace: Dict[str, Any], proposal_data: Dict[str, Any]) -> str:
        """Assemble the grounded prompt payload sent to the model for a single criterion."""
        focus = self.CRITERION_GUIDE.get(criterion, criterion)
        filtered_trace, filtered_proposal = self._filter_for_llm(trace, proposal_data)
        return (
            f"Company: {trace.get('company', proposal_data.get('company_name', 'the company'))}\n"
            f"Executive scope: {trace.get('exec_id', 'Executive Board')}\n\n"
            f"Focus your analysis ONLY on: {focus}\n\n"
            f"Deterministic SML evidence trace:\n{json.dumps(filtered_trace, indent=2)}\n\n"
            f"Remuneration proposal details:\n{json.dumps(filtered_proposal, indent=2)}"
        )

    def _generate_with_gemini(self, criterion: str, lens: str, trace: Dict[str, Any], proposal_data: Dict[str, Any]) -> str:
        """
        Generate a single-criterion insight with Google Gemini, if GEMINI_API_KEY is set
        and the SDK is installed. Returns "" on any miss so callers fall back to templates.

        Configurable purely via environment variables:
          GEMINI_API_KEY      - required to enable Gemini at all
          GEMINI_MODEL        - model id (default: gemini-2.0-flash)
          GEMINI_TEMPERATURE  - sampling temperature (default: 0.3)
          GEMINI_MAX_TOKENS   - max output tokens (default: 600)
        """
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            return ""

        model_name = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
        try:
            temperature = float(os.getenv("GEMINI_TEMPERATURE", "0.3"))
        except ValueError:
            temperature = 0.3
        try:
            max_tokens = int(os.getenv("GEMINI_MAX_TOKENS", "600"))
        except ValueError:
            max_tokens = 600

        system_prompt = self.SYSTEM_PROMPTS.get(lens, self.SYSTEM_PROMPTS["auditor"])
        user_content = self._build_insight_user_content(criterion, trace, proposal_data)

        try:
            import google.generativeai as genai  # lazy import: only needed when key is present

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_prompt,
            )
            response = model.generate_content(
                user_content,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                },
            )
            return (response.text or "").strip()
        except Exception as e:  # noqa: BLE001 - any failure must degrade gracefully
            print(f"[LLM Dual-Lens] Gemini call failed: {e}. Falling back to deterministic template.")
            return ""

    def generate_criterion_insight(self, criterion: str, lens: str, trace: Dict[str, Any], proposal_data: Dict[str, Any]) -> str:
        """
        Public entry point for a single checklist criterion. Tries Gemini first, then
        falls back to a deterministic, grounded template so the UI always has an answer.
        """
        ai_text = self._generate_with_gemini(criterion, lens, trace, proposal_data)
        if ai_text:
            return ai_text
        return self._fallback_insight(criterion, lens, trace, proposal_data)

    def _fallback_insight(self, criterion: str, lens: str, trace: Dict[str, Any], proposal_data: Dict[str, Any]) -> str:
        """Deterministic, offline templates mirroring the original UI answers (grounded in trace values)."""
        company = trace.get("company", proposal_data.get("company_name", "the company"))
        exec_id = trace.get("exec_id", "the Executive Board")
        reach = trace.get("reach_ratio", 1.0)
        mom = trace.get("multiple_of_median", 1.0)
        salary = proposal_data.get("proposed_salary", 0.0) or 0.0
        lti = proposal_data.get("proposed_lti", 0.0) or 0.0
        lti_ratio = trace.get("lti_vs_salary_ratio")
        if lti_ratio is None:
            lti_ratio = (lti / salary) if salary > 0 else 0.0
        esg = proposal_data.get("esg_linked", False)

        templates = {
            "reach": {
                "auditor": f"\U0001f50d Activist Advisor Analysis: SML Quantile Residual mapping indicates {exec_id} at {company} is compensated as if running a company {reach:.1f}x its actual economic scale. This signals unearned rent extraction with no size-elasticity justification. We recommend voting AGAINST.",
                "compliance": f"\U0001f6e1️ Corporate Board Counsel Defense: The {reach:.1f}x size premium for {company} reflects a vital global retention necessity in an internationally competitive CEO marketplace. Under DCGK Sections G.2 & G.9, it captures operating complexity not reflected in simple European scale metrics.",
            },
            "ratchet": {
                "auditor": "\U0001f50d Activist Advisor Analysis: Our panel regression flags an asymmetric ratchet (pay-for-luck): compensation escalated on positive performance yet stayed insulated during ROA contraction, transferring wealth from shareholders to the board.",
                "compliance": "\U0001f6e1️ Corporate Board Counsel Defense: Compensation adjustments were driven by contractual long-term restructuring milestones independent of cyclical ROA shocks; disclosure of these milestones satisfies DCGK Section G.10.",
            },
            "mom": {
                "auditor": f"\U0001f50d Activist Advisor Analysis: Total compensation is {mom:.2f}x the shadow-peer cluster median, breaching the ISS high-concern threshold of 1.50x and confirming the package is a statistical outlier.",
                "compliance": f"\U0001f6e1️ Corporate Board Counsel Defense: The {mom:.2f}x multiple reflects a peer index that does not capture {company}'s specialized global footprint; the board applies a customized international peer set compliant with DCGK G.2.",
            },
            "secrecy": {
                "auditor": "\U0001f50d Activist Advisor Analysis: The board opted out of individual compensation disclosure under § 286 Abs. 5 HGB. This secrecy flag is a critical accountability risk and correlates with a documented pay premium.",
                "compliance": "\U0001f6e1️ Corporate Board Counsel Defense: The individual opt-out was approved by a supermajority shareholder resolution and complies fully with German HGB transparency statutes.",
            },
            "ltiRatio": {
                "auditor": f"\U0001f50d Activist Advisor Analysis: The LTI-to-salary ratio of {lti_ratio:.2f}x, compounded with a size-inflated base, amplifies unearned payouts even under median market performance.",
                "compliance": f"\U0001f6e1️ Corporate Board Counsel Defense: The {lti_ratio:.2f}x long-term tilt deliberately aligns the majority of pay with multi-year shareholder return (TSR) under DCGK Section G.1.",
            },
            "esg": {
                "auditor": "\U0001f50d Activist Advisor Analysis: ESG linkages lack quantifiable, audited carbon metrics and read as a symbolic 'greenwashing' shield rather than a binding performance condition." if not esg else "\U0001f50d Activist Advisor Analysis: While ESG targets are present, their weighting and measurability must be independently verified before they can offset the quantitative pay anomalies above.",
                "compliance": f"\U0001f6e1️ Corporate Board Counsel Defense: Variable STV/LTI payouts are anchored to quantifiable carbon-reduction and diversity targets under DCGK Section G.1." if esg else "\U0001f6e1️ Corporate Board Counsel Defense: The board should introduce quantifiable ESG/sustainability targets to satisfy DCGK Section G.1 and pre-empt proxy-advisor criticism.",
            },
            "stretch": {
                "auditor": f"\U0001f50d Activist Advisor Analysis: SML component decomposition flags a Hidden Stretch in variable components (variance: {trace.get('hidden_stretch_variance', 0.0):.2f}). This confirms the board is hiding bloated payouts inside lumpy options or STI targets rather than base pay. We recommend voting AGAINST.",
                "compliance": f"\U0001f6e1️ Corporate Board Counsel Defense: The component divergence reflects a deliberate DCGK-compliant design maximizing variable incentive weight under G.10; the option/LTI variance aligns with multi-year performance milestones.",
            },
            "concentration": {
                "auditor": f"\U0001f50d Activist Advisor Analysis: The internal concentration ratio C_jt is {trace.get('internal_concentration_ratio', 1.0):.2f}x, indicating excessive CEO payout relative to other executive board members (ratchet triggered: {trace.get('concentration_ratchet_triggered', False)}). This represents poor internal equity. We recommend voting AGAINST.",
                "compliance": f"\U0001f6e1️ Corporate Board Counsel Defense: The CEO-to-median-board ratio is justified by the unique responsibilities, global experience, and market value of the chief executive in accordance with DCGK Section G.3.",
            },
        }
        lens_map = templates.get(criterion)
        if not lens_map:
            return "No segment narrative generated."
        return lens_map.get(lens, lens_map.get("auditor", "No segment narrative generated."))

    def _generate_fallback_chat_response(self, mode: str, trace: Dict[str, Any], proposal_data: Dict[str, Any], user_query: str) -> str:
        """
        Parses the user query for key governance and econometric terms
        and dynamically routes to the relevant SML Single-Criterion fallback templates.
        """
        if not user_query:
            return ""
        q = user_query.lower()
        
        # 1. Reach/Size premiums
        if "reach" in q or "size" in q or "premium" in q or "scale" in q:
            return self._fallback_insight("reach", mode, trace, proposal_data)
            
        # 2. Asymmetric ratcheting/pay-for-luck
        elif "ratchet" in q or "luck" in q or "downside" in q or "performance" in q:
            return self._fallback_insight("ratchet", mode, trace, proposal_data)
            
        # 3. Multiple of Median/ISS checks
        elif "mom" in q or "median" in q or "peer" in q or "iss" in q or "limit" in q:
            return self._fallback_insight("mom", mode, trace, proposal_data)
            
        # 4. Disclosure secrecy HGB § 286
        elif "secrecy" in q or "disclosure" in q or "opt-out" in q or "hgb" in q:
            return self._fallback_insight("secrecy", mode, trace, proposal_data)
            
        # 5. LTI ratios and DCGK G.1
        elif "lti" in q or "ratio" in q or "salary" in q or "fixed" in q or "balance" in q:
            return self._fallback_insight("ltiRatio", mode, trace, proposal_data)
            
        # 6. ESG indicators and carbon targets
        elif "esg" in q or "carbon" in q or "green" in q or "sustainability" in q:
            return self._fallback_insight("esg", mode, trace, proposal_data)

        # 7. Stretch / Divergence
        elif "stretch" in q or "divergence" in q or "skew" in q or "bucket" in q:
            return self._fallback_insight("stretch", mode, trace, proposal_data)
            
        # 8. Concentration / CEO ratio
        elif "concentration" in q or "equity" in q or "ceo ratio" in q or "board ratio" in q:
            return self._fallback_insight("concentration", mode, trace, proposal_data)
            
        return ""

    def _fallback_auditor_report(self, trace: Dict[str, Any], proposal_data: Dict[str, Any]) -> str:
        """Deterministic high-fidelity offline template for the activist auditor report."""
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
5. **Component Stretch & Concentration:** We detect a hidden stretch of **{trace.get('hidden_stretch', 0.0)*100:.1f}%** across variable components (variance: **{trace.get('hidden_stretch_variance', 0.0):.2f}**). CEO internal board concentration ratio is **{trace.get('internal_concentration_ratio', 1.0):.2f}x** (ratchet triggered: **{trace.get('concentration_ratchet_triggered', False)}**).

### Econometric Evidence & Metrics
* **Shadow Peer Universe:** Cluster {cluster_id} (Grouped by Asset Turnover, ROA, and Gearing).
* **Multiple of Median (MoM):** **{multiple_of_median:.2f}x** the cluster median pay (exceeding ISS high-concern threshold of 1.5x).
* **Proposed Target Pay:** €{actual_pay:,.2f} vs Peer Median €{cluster_median_pay:,.2f}

**Conclusion:** This package represents a Transfer of Wealth from shareholders to the Executive Board without corresponding downside risk. We urge institutional clients to vote **AGAINST**."""
        return report

    def generate_auditor_report(self, trace: Dict[str, Any], proposal_data: Dict[str, Any], user_query: str = None) -> str:
        """
        Generates the Activist Investor / Proxy Advisor audit report (VOTE AGAINST).
        Supports custom conversational queries with intelligent keyword fallback routing.
        """
        # Try API first
        api_report = self._generate_narrative_with_api("auditor", trace, proposal_data, user_query)
        if api_report:
            return api_report
            
        # If user query is provided, check for keyword fallback routing
        if user_query:
            fallback_response = self._generate_fallback_chat_response("auditor", trace, proposal_data, user_query)
            if fallback_response:
                return fallback_response
            
        # Fallback to deterministic high-fidelity templates
        return self._fallback_auditor_report(trace, proposal_data)

    def _fallback_compliance_report(self, trace: Dict[str, Any], proposal_data: Dict[str, Any]) -> str:
        """Deterministic high-fidelity offline template for the corporate board compliance report."""
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

4. **Internal Concentration ({trace.get('internal_concentration_ratio', 1.0):.2f}x) & Hidden Stretch:**
   * *The Threat:* High internal board concentration ratio and component divergence (hidden stretch of {trace.get('hidden_stretch', 0.0)*100:.1f}%) will trigger concerns over internal equity and transparency.
   * *Board Defense (DCGK G.3):* Justify the concentration ratio based on unique CEO scale responsibilities, and argue that variable option variance is designed strictly to incentivize multi-year performance milestones under G.10.

### Action Plan for Board Communication
* **Preemptive Disclosure:** Draft a supplementary corporate governance statement detailing the global peer comparison methodology used by the supervisory board.
* **Shareholder Outreach:** Schedule 1-on-1 engagement calls with top 10 institutional shareholders to proactively explain the size premium and contract conditions.
* **Governance Review:** Integrate the proposed {esg_text} to satisfy ISS sustainability alignment checks."""
        return report

    def generate_compliance_report(self, trace: Dict[str, Any], proposal_data: Dict[str, Any], user_query: str = None) -> str:
        """
        Generates the Corporate Board / Defense report.
        Supports custom conversational queries with intelligent keyword fallback routing.
        """
        # Try API first
        api_report = self._generate_narrative_with_api("compliance", trace, proposal_data, user_query)
        if api_report:
            return api_report
            
        # If user query is provided, check for keyword fallback routing
        if user_query:
            fallback_response = self._generate_fallback_chat_response("compliance", trace, proposal_data, user_query)
            if fallback_response:
                return fallback_response
            
        # Fallback to deterministic high-fidelity templates
        return self._fallback_compliance_report(trace, proposal_data)

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
