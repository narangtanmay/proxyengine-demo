# ProxyEngine: Technical Specification & System Design

## 1. Product Context & Objectives
**Product Name:** ProxyEngine (The Say-on-Pay Terminal)
**Objective:** An automated, econometric auditing tool that evaluates German executive compensation against market baselines and governance rules.
**Core Differentiator:** Combines an LLM-driven PDF extraction layer (to standardize unstructured remuneration reports) with a 7-stage deterministic Statistical Machine Learning (SML) pipeline. It outputs an NDA-safe Dual-Lens interface to simulate Proxy Advisor audits vs. Corporate Board compliance checks.
**Proof of Concept (POC) Goal:** As explicitly validated by the TUM supervisors, the final demo will showcase a user uploading a raw remuneration PDF. The system extracts the pay structure, maps it to our mathematical baseline, and algorithmically audits its alignment with the peer group.

## 2. Methodology & Academic Rigor (The "Math Flex")
To ensure analytical rigor, our pipeline eschews black-box predictive models in favor of interpretable Statistical Machine Learning (SML). First, to counter the opportunistic "Lake Wobegon" effect in self-selected peer benchmarking, we apply unsupervised K-Means clustering on fundamental firm characteristics (Operating Revenue, ROA, and Gearing) to construct mathematically objective "Shadow Peers." We then model baseline expected compensation using a Lasso-Regularized Quantile Regression at the median ($\tau = 0.5$). This method is robust to megacap outliers and allows us to anchor and validate our model against the empirically established firm-size elasticity of executive pay ($\beta \approx 0.3$).

The unexplained residual from this baseline forms our primary anomaly metric (the "Reach" ratio). We subsequently apply fixed-effects dummy-variable panel regressions to identify "Asymmetric Ratchets"—testing empirically whether executive compensation exhibits "pay-for-luck" by rising during positive ROA shocks while remaining statistically insulated during downturns. These deterministic outputs are then evaluated against proxy-standard metrics and hard statutory constraints (e.g., LTI vs. STI balance per § 87 AktG) to trigger our final compliance flags.

## 3. Data Dictionary & Ground Truth Variables
*All modeling relies strictly on these pre-defined variables to prevent multicollinearity and data dredging.*
*   **Size:** `opre` (Operating Revenue). Fallback: `toas` (Total Assets).
*   **Performance:** `roa` (Return on Assets). Fallback: `roe`.
*   **Leverage:** `gear` (Gearing). Fallback: `solr`.
*   **Dependent Variable (Pay):** `total_comp` (Clean flow pay, excluding lumpy pensions).
*   **Keys:** Firm = `isin` / `sd_isin`. Person = `exec_id`. Time = `year`.
*   **External Inputs Required:** `cpi_t` (Consumer Price Index for inflation deflation).

## 4. The SML Pipeline (7-Stage Data Flow)

### Part -1: The PDF Extraction POC (The Input Layer)
*   **The Problem:** Remuneration structures are buried in unstructured PDFs, making standardisation impossible.
*   **The Execution:** A fine-tuned LLM (or highly prompted frontier model) parses an uploaded XML/PDF remuneration report and extracts the proposed pay components (`salary`, `sti`, `lti_grants`) into our standardized JSON schema.
*   **The Output:** A structured payload ready to be benchmarked against the historical panel.

### Part 0: Data Cleaning (The Foundation)
*   **Annualization:** `pay_ann = pay_raw * (Lit / dit)` (Scales partial-year compensation to 365 days).
*   **Deflation:** `pay_real = pay_ann / (cpi_t / cpi_base)` (Removes 15-year inflation illusion).
*   **Output:** Two panels sharing ORBIS features: `Firm-Year` and `Person-Year`.

### Part 1: Normal Pay Baseline (The Curve)
*   **Math:** Quantile Regression ($\tau = 0.5$): $Q_{0.5}(\log(\text{pay})) = \alpha + \beta\log(\text{opre}) + \gamma_1(\text{roa}) + \gamma_2(\text{gear}) + \delta_t$
*   **Validation:** Size elasticity $\beta$ must $\approx 0.3$.
*   **Output:** The expected pay curve, the residual ($\varepsilon_{it}$), and the year effect ($\delta_t$).

### Part 2: The Gap as "Reach" (Flag 1)
*   **Math:** $\text{Reach}_{it} = \exp(\varepsilon_{it} / \beta)$
*   **Definition:** "Paid like a firm $X$ times your actual size."

### Part 3: Divergence / Hidden Stretch (Flag 2)
*   **Math:** Re-run Parts 1-2 for 6 non-overlapping pay buckets (Salary, STI, LTI Grants, Stock, Options, Other).
*   **Definition:** Calculates the variance across the Reach vector. High variance indicates excess is hiding in complex equity buckets.

### Part 4: The Treadmill (Market-wide Drift)
*   **Math:** Oaxaca-Blinder decomposition across time.
*   **Definition:** Splits total pay growth into fundamentals (firms getting bigger/better) vs. drift (the benchmark curve shifting upward).

### Part 5: Portable Rent / Mobility (Flag 3)
*   **Math:** Track `exec_id` across firms. 
*   **Definition:** Event study tracking if a CEO's personal "Reach" premium survives when they change employers (proving pay is for the person, not the seat). *Note: Gate this on Day 1 by counting distinct ISINs per exec_id.*

### Part 6: Assembling Red Flags (The Deliverable)
*   **Asymmetric Ratchet:** $\Delta\log(\text{pay}) = \alpha + \beta_{\uparrow}\Delta\text{roa}^+ + \beta_{\downarrow}\Delta\text{roa}^-$. Flag if $\beta_{\uparrow} \gg \beta_{\downarrow} \approx 0$.
*   **Secrecy Premium:** Flag if firms with `opting_out` = 1 show statistically higher Reach.
*   **Internal Concentration:** Ratio of CEO pay to median other executive pay ($C_{jt}$). Flag if it ratchets up over time.

## 5. The LLM Translation Layer & UI (The Dual-Lens Interface)

### 5.1 Deterministic UI / LLM Constraint
Rather than deploying an open-ended generative chat interface—which introduces severe risks of analytical hallucination in a financial context—our architecture restricts the Large Language Model (LLM) to act strictly as a deterministic translation layer. The econometric engine outputs a rigidly defined "Evidence Trace," consisting exclusively of our pre-calculated mathematical flags (e.g., the Reach ratio, Asymmetric Ratchet coefficients, and AktG § 87 compliance checks). The user interface then contextualizes these hard metrics through a Dual-Lens framework: an **Auditor View** (generating external proxy voting recommendations) and a **Compliance View** (generating internal board warnings). By constraining the LLM to synthesize only these mathematically proven anomalies, we guarantee that every narrative insight maintains a transparent, verifiable audit trail directly back to the foundational financial data.

### 5.2 Input Schema (NDA-Safe)
The backend passes a strict JSON Evidence Trace to the LLM containing ONLY the mathematical outputs from Part 6, stripping all raw financial totals.
*Example Payload:* `{"reach": 2.4, "hidden_stretch_variance": 4.1, "asymmetric_ratchet": {"up_beta": 0.4, "down_beta": 0.01}, "secrecy_premium": true}`

### 5.3 The UI Interaction
A single React/Streamlit dashboard displaying the "Reach" scatterplot. A global toggle switch alters the LLM System Prompt:

*   **Mode A: The Auditor (Proxy Advisor / Investor Lens)**
    *   *System Prompt:* "You are an ISS proxy advisor. Evaluate the statistical flags and draft a ruthless 'Say-on-Pay' voting recommendation."
    *   *Output:* "VOTE AGAINST. The board exhibits a 2.4x Reach ratio, driven by a 'Hidden Stretch' in option grants. An asymmetric ratchet confirms the CEO is insulated from the firm's recent ROA decline. The firm's choice to opt-out of individual disclosure further compounds governance risk."
*   **Mode B: The Defender (Corporate Board Lens)**
    *   *System Prompt:* "You are corporate counsel. Review the statistical flags and draft a defense or compliance warning based on DCGK guidelines."
    *   *Output:* "COMPLIANCE WARNING: Our current structure risks an ISS rejection. To defend the 2.4x Reach, we must publicly link the option grant variance to specific strategic milestones. We must also introduce a strict downside clawback to neutralize the asymmetric ratchet penalty."

## 6. Day 1 Hackathon Execution Checklist
1. **The Day-One Gate:** Run `count(distinct isin)` grouping by `exec_id`. If movers > 50, Part 5 (Portable Rent) is fully viable. If thin, drop Part 5 and rely on the Secrecy Premium / Asymmetric Ratchet.
2. **Data Pipeline Verification:** Hand-code Part 0 and Part 1 for a single company to confirm $\beta \approx 0.3$. Do not build the UI until the $\beta$ validation passes.
3. **External Inputs:** Find and import a standard European CPI inflation index CSV for the Part 0 deflation math.