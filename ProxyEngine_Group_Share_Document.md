# ProxyEngine: Hackathon Execution Playbook & Domain Guide

## 1. Executive Summary: What We Are Building

**One-line pitch:** *ProxyEngine catches executives who are overpaid for the size of their company — and proves it with a number.*

We are building an automated **Say-on-Pay analysis platform**. Executive remuneration reports are opaque, and boards routinely justify high CEO pay by selecting weak, self-serving peer groups — a documented phenomenon in the governance literature (the "Lake Wobegon effect," where every board claims its CEO is above average). ProxyEngine standardizes these reports and acts as an automated proxy advisor: it builds objective peer groups from firm economics, estimates expected pay, and flags anomalies against German corporate-governance law (AktG, DCGK) and the EU Shareholder Rights Directive II / ARUG II framework.

**The Target Audience:**
1. **Corporate reporting departments (PRIMARY user)** — the listed company's own remuneration team, which must publish these reports by law. They use ProxyEngine to build a methodically-derived peer group and standardize + self-audit a pay structure *before* publishing, against DCGK and proxy-advisor expectations. *This is the use case the challenge chair explicitly endorsed in the kickoff, and the one Liam's domain notes are built around — lead the pitch with it.*
2. **Activist investors / asset managers** — the mirror user: audit a published package to decide how to vote at the AGM.

**The core thesis (our differentiator):** Executive-pay analysis is inherently adversarial. The *same* statistical residual supports a "vote against" for an activist and a "compliance fix" for a board. One engine, two lenses. (See Section 4.)

---

## 2. The Data Schema (Ground Truth Variables)

*We deliberately restrict ourselves to the variables provided in the 15-year dataset to avoid multicollinearity and data dredging.*

> **✅ Schema verified (2026-06-20):** The compensation panel is `company_year.csv` (1,468 firm-years), `person_year.csv` (6,727 person-years), and `company_person.csv` (1,722 execs, link table), for **2008–2020**. Join keys are clean: `isin` + `year` → ORBIS (via `SD_ISIN`); `company_person_id` / `exec_id` link the person tables. `opting_out`, `ceo_flag_eoy`, `cfo_flag_eoy`, and the full pay decomposition are all present — plus bonus governance vars: `female`, `nationality`, `date_of_birth`, board entry/exit dates (→ tenure, age, gender controls + a diversity angle). **There is no entity-matching problem; ISIN is the universal key.**
>
> **⚠️ The real data task — format harmonization, not joining:** 2008–2020 is clean CSV, but **2021 is missing** and **2022/2023/2024 are messy yearly Excels** (the "DSW Studie" report: a banner row in row 1, a ~113-column wide `Compensation2024` sheet, ~43-row `Companies` sheets). The genuine Friday work is parsing these offset/wide reports and concatenating them onto the panel. **Still unconfirmed: the exact `TSR`/`EPS`/ESG column names** (header row is offset in the Excel) — the pay-for-performance flags depend on these, so locate them first thing.

### Baseline & Peer-Grouping Attributes (from ORBIS)
*   **`opre` (Operating Revenue):** proxy for firm size/scale.
*   **`roa` (Return on Assets):** proxy for firm efficiency.
*   **`gear` (Gearing):** proxy for capital structure/risk.

### Compensation Attributes (from BOARD / PERSON files)
*   **`total_comp`** — clean flow pay (excludes lumpy pensions). Basis for expected pay and the "Reach" calculation.
*   **Pay-component decomposition:** `salary`, `one_year_bonus` (STI), `multi_year_bonus_grants` (LTI), `stock_grants`, `option_grants`. Used to show *where* excess pay is concentrated across fixed, short-term, and equity buckets.

### Governance-Flag Attributes (inputs to the narrative layer)
*   **`opting_out`** *(BOARD file)* — if 1, the firm declined individual pay disclosure. Triggers a **non-disclosure flag**.
*   **`ceo_flag_eoy`** *(PERSON file)* — identifies the CEO. Used for **internal pay concentration** (CEO pay ÷ median board pay).
*   **`STI_total_ESG_Share`** *(ESG 2024 Excel)* — used for an **ESG–performance misalignment flag** (e.g., ROA falls but ESG-linked payouts stay maxed out).
*   **`TSR`** and **`EPS`** *(Comp 2024 Excel)* — used for pay-for-performance alignment tests.

---

## 3. The 4-Stage Analysis Pipeline

*The judging panel is 2 finance + 1 technical (informatics) judge, with no formal rubric — they reward a strong, well-reasoned idea over raw model accuracy.*

**On model choice — do not pitch this as "accurate vs explainable."** That is a false binary, and the technical judge will know it: SHAP makes a gradient-boosted model auditable too (it can decompose a package into size-driven vs performance-driven vs unexplained €). Our argument is sharper and more correct (see Step 2): **our product is residual-based anomaly detection, not prediction.** A high-capacity model fits the overpayment *itself*, shrinks the residual, and hides the very flags we exist to surface. So we deliberately model only the *legitimate* pay drivers with a transparent **quantile regression**, leaving rent in the residual. We still build a **gradient-boosted model + SHAP** — but as a **secondary "what drives pay" exhibit** to satisfy required deliverable #3 (explainable AI) and the technical judge, **not** as the anomaly engine.

> **Map to the brief — protect the required core first.** Deliverables #1 (predictive comp model), #2 (peer benchmarking), and #3 (driver explainability) are **required**. Red-flag detection (#4) and the dashboard (#5) are **[Optional]**. Our most eye-catching assets — the Reach/Ratchet flags and the Dual-Lens toggle — live on the *optional* deliverables. They are our differentiator, but they must **not** be built at the expense of a working #1–#3.

### Step 1: Peer Groups — Industry First, Then Algorithmic Refinement
*   **The Problem:** The internal ORBIS extract has no `sector`/`industry` column. **But the challenge brief explicitly lists industry as an expected input *and* explicitly invites external enrichment via APIs** — so "no industry, therefore we cluster" is a self-imposed framing a judge who read the brief will push back on.
*   **The Approach (revised):** First **enrich industry** where feasible — we hold `SD_ISIN` and `lei_LEI`, so a sector/NACE code is one external lookup away. Then use **K-Means clustering** on standardized `opre`, `roa`, and `gear` as a *within-* or *cross-industry refinement* that captures economic profile (scale, efficiency, leverage) beyond a coarse sector label.
*   **Why both:** Pure clustering with no sector guard groups a software CEO with a chemicals CEO because their margins match — economically illiterate, and a known weakness (our own prior council flagged it; the fix is "sector constraints before clustering"). Pure industry labels let boards hand-pick flattering peers — the documented Lake Wobegon problem. Combining them is the defensible position.
*   **Honest limitation (state it before a judge asks):** With three scale-correlated variables, clustering alone sorts substantially on *size*, which the Step 2 regression already controls for. So we present clustering as **a refinement and robustness check on peer selection**, not the load-bearing result.

### Step 2: The Baseline (Regularized Quantile Regression)
*   **The Method:** **Lasso-regularized quantile regression** at the median ($\tau = 0.5$) modelling $\log(\text{pay})$ on $\log(\text{size})$ plus a small set of legitimate performance controls. OLS is distorted by megacap outliers; median quantile regression is robust to them.
*   **Why the parsimonious baseline is *correct*, not merely *safe* (this is the load-bearing argument):** Our goal is **not** to predict pay as accurately as possible. It is to estimate what pay *should* be from legitimate drivers, so that everything unjustified remains visible in the residual. A flexible model (XGBoost, deep nets) would fit the overpayment along with everything else — it **explains away the rent we are trying to detect**, shrinking residuals toward zero and silencing our flags. In anomaly detection, the higher-$R^2$ model is the *worse* tool. The simple, well-specified baseline is therefore the more accurate model *at the job that matters*. The pitch line:
    > "Predicting pay accurately is the easy, wrong goal — a flexible model just memorises the overpayment. We model only the legitimate drivers, so everything a board can't justify stays visible in the residual. **That residual is the product.**"
*   **Why this also beats post-hoc SHAP for compliance:** the decomposition here **is** the model (a defensible $\beta$), not a correlational, background-dependent approximation of a black box. For a tool that must survive a board's lawyers, "this is what the model literally computes" beats "this is our explanation of what the model probably did."
*   **The Sanity Check (corrected framing):** We expect a size elasticity ($\beta$) near **0.3**. This is **not** an arbitrary target or a validation of our join — it is the canonical cross-sectional pay-to-size elasticity documented across decades and countries: Roberts' Law; Kostiuk (1990); Murphy (1999) survey; Gabaix & Landier (2008, $\kappa \approx 1/3$); Frydman & Saks (2007). If our $\beta$ lands near 0.3, we report it as *consistent with the literature*. We explicitly note it is a **regularity, not a universal constant** — it rises toward ~0.5 for small private firms and weakens for the smallest listed firms. Join integrity is verified separately, by row-count and coverage checks (see Step 0 gate), **not** by the value of $\beta$.

### Step 3: Anomaly Detection (The Flags)

> **Sharpen the framing — these aren't "bad governance," several are statutory breaches.** Liam's `Facts and Definitions Wiki` quotes the actual law: **§ 87 AktG** requires that (a) remuneration be *in relation to performance*, (b) **LTI must outweigh STI**, and (c) **if the firm is in economic difficulty the supervisory board *must reduce* total remuneration**. **§ 87a AktG** mandates an explicit maximum-compensation cap and disclosed performance metrics. That means two of our flags map to *legal duties*, not opinions — which is far more defensible in front of finance/accounting judges than "pay for luck."

1.  **The "Reach" Ratio** *(our headline metric):* we translate the regression residual into plain English. $\text{Reach} = \exp(\varepsilon / \beta)$. Output: *"This CEO is paid like a firm 2.4× bigger."* This is the one number the whole demo is built around.
2.  **LTI-vs-STI Balance (§ 87 AktG / DCGK) — cheapest high-confidence flag, build this first:** a trivially computable check — does `multi_year_bonus_grants` (LTI) outweigh `one_year_bonus` (STI)? If not, it is a direct § 87 AktG breach. No regression, no residual, uses columns we have confirmed. Near-zero build cost, maximum legal defensibility — this is the flag to demo if everything else slips.
3.  **Pay-for-Luck → § 87 AktG "downturn duty" breach:** a dummy-variable panel regression, $\Delta\text{Pay} = \alpha + \beta_1(\Delta\text{ROA}_{\text{up}}) + \beta_2(\Delta\text{ROA}_{\text{down}})$. If pay rises on good ROA but is insulated on bad ROA ($\beta_2 \approx 0$), pay was *not* reduced in a downturn — which § 87 AktG says the board **must** do. We frame it as both the academic "pay for luck" result (Bertrand & Mullainathan 2001) *and* a statutory red flag. Much stronger than either alone.
4.  **Cross-Firm Premium Persistence** *(stretch — now more feasible than first thought):* `exec_id` is confirmed present as a stable person-level key across firms, so tracking an executive's premium across employers is doable, not the data nightmare we feared. Still the last thing to build, but no longer "first to cut" — promote it if the core flags land early.

### Step 4: The Narrative Layer (Grounded, Non-Hallucinating)
*   **The Rule:** The LLM does **not** reason about finance or invent figures. It is a constrained natural-language templating engine.
*   **The Execution:** The backend passes a strict JSON payload containing *only* the triggered numeric flags and their values. The LLM converts them into prose; every quantitative claim in the output traces to a field in that payload.
*   **The Output:** A short, governance-grounded recommendation with inline citations to the triggering metrics. Outputs are framed as **flags for human review**, not automated verdicts (see ethics note in Section 6).

---

## 4. The UI / UX: The Dual-Lens Toggle

We build **one** dashboard with a single toggle. The analytical backend is identical across both modes — only the narrative system prompt changes, demonstrating that one objective residual drives both sides of a real proxy fight.

*   **Mode 1 — The Auditor (activist / proxy-advisor lens)**
    *   *Framing:* a ruthless shareholder-side voting recommendation.
    *   *Example:* "Recommendation: VOTE AGAINST. Pay implies a Reach of 2.4× the firm's size. Pay-for-luck asymmetry detected: base pay rose 12% while ROA fell 4%."
*   **Mode 2 — The Board Advisor (corporate / compliance lens)**
    *   *Framing:* a pre-publication compliance warning.
    *   *Example:* "COMPLIANCE WARNING: This structure risks a proxy-advisor rejection. The Reach ratio triggers our anomaly threshold. To align with DCGK, cap the LTI or tie the 12% base increase to explicit ESG/TSR metrics."

This is the feature judges will remember. It is also cheap to build — two system prompts over one backend.

---

## 5. Day 1 Execution Plan (Friday Morning)

**Critical path = the data join.** Everything downstream is worthless if firm financials, compensation records, and `exec_id` don't link. De-risk it first, and unblock the team with a contract.

1.  **Agree the JSON contract (all 5, first 30 min):** define the exact schema the backend returns (`reach`, `residual`, `beta`, triggered flags). Export a **fake but schema-correct** sample immediately so backend and UI are never blocked waiting on data.
2.  **Mikhail & Shivani (Data/Math):** Do **not** clean the full 15-year dataset on Day 1. **Hand-build a 3-row lookup CSV** for VW, Bayer, SAP (eyeball the identifiers — 30 minutes; fuzzy auto-matching is a 6-hour hole). Push those rows through the join → quantile regression → one real Reach number, end-to-end and ugly. Watch for German Excel encoding (umlauts, comma decimals, merged headers) and fiscal-vs-calendar-year misalignment.
3.  **Tanmay (Backend/LLM):** Stand up the FastAPI server against the fake JSON contract. Write the constrained prompt templates that ingest flags and emit the two lens narratives.
4.  **Saket (UI):** Build the dashboard against the fake JSON — the Reach scatterplot and the Dual-Lens toggle. Highlight the exact flags the narrative is reading.
5.  **Liam (Domain):** Map ORBIS variables to ISS/Glass Lewis and DCGK guidelines. Write the exact thresholds for the pay-for-luck flag and the DCGK compliance language. Draft the legal/ethics disclaimer (Section 6).
6.  **End of Day 1 target (walking skeleton):** one CSV → merged dataframe → plain quantile regression → one residual → one Reach number → JSON → FastAPI → two-lens narrative on screen. Swap real numbers for fake ones on Day 2; then freeze.

**Cut order under time pressure:** (1) cross-firm premium persistence, (2) pay-for-luck panel regression, (3) Lasso regularization (plain quantile regression is fine), (4) K-Means (hardcode the 3 firms as one peer group for the demo). Keep the toggle — it is the wow moment and costs nothing.

---

## 6. Risk, Ethics & Reproducibility

*The council flagged these as the gaps most likely to cost us with academic judges. Address them on a slide.*

*   **Reputational / legal exposure:** Publicly labelling *named, real* DAX CEOs as "overpaid" with an automated "VOTE AGAINST" carries defamation and data-protection risk. In the live demo, **pseudonymize firms** ("Firm A") or add an explicit disclaimer that outputs are model-generated flags for human review, not assertions of fact.
*   **Honest limitations slide:** small sample (DAX/MDAX), clustering sorts partly on size, no causal identification claimed, elasticity is a regularity not a constant. Stating limits *earns* credibility with this audience; hiding them invites the question that kills you in Q&A.
*   **Reproducibility:** fix random seeds, version the input data, and keep an audit trail from each output sentence back to its triggering metric. This is exactly what accounting faculty reward.
*   **Pitch structure:** open with the plain-language hook ("overpaid for the size of their company — proven with a number"), then immediately demonstrate rigour (citations, honest limits, the Dual-Lens toggle). Plain line opens the door; the econometrics wins the room.
