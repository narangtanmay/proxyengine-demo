# Final Hackathon Strategy: ProxyEngine 

## 1. The Core Identity & Positioning
**Product Name:** ProxyEngine
**Target Customer:** Institutional Investors and Activist Hedge Funds.
**The Pitch:**
"Before launching a proxy fight over executive compensation, institutional investors need mathematically bulletproof evidence of rent extraction and the ability to anticipate the corporate board's legal defense. 

We built **ProxyEngine**, an Adversarial AI platform for 'Say-on-Pay' wargaming. It ingests German corporate data, uses regularized econometric models to define expected compensation, and mathematically isolates executive rent extraction (e.g., 'Portable Rent', 'Asymmetric Ratchets'). Finally, an NDA-compliant LLM translates these complex statistical flags into an adversarial wargame: generating both the investor's attack thesis and the board's DCGK compliance defense."

## 2. The Architecture & Econometric Pipeline
*A unified, dependency-driven pipeline. Output of Step A feeds Step B.*

### Step 0: The Panel & "Shadow Peer" Clustering
*   **The Reality Check:** The dataset **does not contain sector or industry labels**. Most teams will panic or manually label data. We turn this into a feature.
*   **The Clustering Math:** We use unsupervised K-Means clustering on three fundamental ORBIS variables to algorithmically group companies by economic physics rather than arbitrary industry labels:
    *   `opre` (Operating Revenue) - Clusters by scale/size.
    *   `roa` (Return on Assets) - Clusters by efficiency (acting as a mathematical proxy for sector, separating asset-light tech from asset-heavy manufacturing).
    *   `gear` (Gearing) - Clusters by capital structure/risk.
*   **The Output:** A unified panel clustered into objective "Shadow Peers" (N ≈ 3,750).

### Step 1: The Baseline (SML Quantile Regression)
*   **The Trap Avoided:** 200 features on 3,750 rows is a high-dimensionality trap. We reject black-box "Pure ML" (like Random Forests) which finance professors distrust, and use objective **Statistical Machine Learning (SML)**.
*   **The Math:** We run a **Lasso-Regularized Quantile Regression** to find the median ($\tau = 0.5$) expectation. The Size Elasticity ($\beta$) will strictly converge to $\approx 0.3$. 
*   **Academic Validation:** Cite *Mäkinen (2007)* and *Gabaix & Landier (2008)*, which empirically prove that firm-size elasticity of CEO compensation is universally $\approx 0.3$. By using Quantile Regression over OLS (citing *Hallock et al., 2010*), we mathematically prevent outlier megacap payouts from dragging the baseline.

### Step 2: The Flags (Deterministic SML Anomaly Detectors)
*Do not attempt to build all six in 48 hours. Focus on the most viable, mathematically rigorous flags.*
*   **Flag 1: The "Reach" Metric:** Translate the statistical residual into a business ratio. $\text{Reach} = \exp(\varepsilon / \beta)$. Output: *"Paid like a firm 2.4x bigger."*
*   **Flag 2: Asymmetric Ratcheting ("Pay for Luck"):** Run a dummy-variable panel regression across the firm-years: $\Delta \text{Pay} = \alpha + \beta_1 (\Delta \text{ROE} \times D_{\text{up}}) + \beta_2 (\Delta \text{ROE} \times D_{\text{down}})$. 
    *   *Academic Validation:* Cite *Garvey & Milbourn (2006)*, the seminal paper proving asymmetric benchmarking. If $\beta_1$ is large but $\beta_2 \approx 0$, we have undeniable, deterministic proof the CEO is shielding downside risk.
*   **Flag 3: ISS Quantitative Alignment Metrics:** Hardcode the exact SML tests ISS uses.
    *   *Multiple of Median (MoM):* Total Pay / Median Peer Pay.
    *   *Relative Degree of Alignment (RDA):* Pay Percentile Rank vs TSR Percentile Rank over 3 years.
*   **Flag 4: Portable Rent (The Stretch Goal):** Use the `exec_id` in the person-year panel to track executives moving across companies. Prove mathematically that their "Reach" premium travels with them.

## 3. The LLM Translation Layer & UI (Deterministic Wargaming)
*   **The Rule:** The LLM cannot hallucinate. It is restricted to a pure natural language templating engine reading from deterministic SML outputs.
*   **The UI Concept:** A single dashboard with an **"Adversarial Wargaming Toggle"**. 
*   **The Execution:** Both modes read from the *exact same* underlying ML math (Reach, Ratchets). The system prompt swaps to simulate the boardroom fight.
*   **Mode 1: The Attack (Investor Lens):**
    * *System Prompt:* "You are an activist investor. Use these mathematical flags to write a ruthless voting recommendation against the board."
    * *Output Example:* "Recommendation: VOTE AGAINST. Executive compensation implies an unmerited 'Reach' of 2.4x their firm size. Asymmetric Ratchet detected: base pay increased 12% despite a 4% ROIC contraction."
*   **Mode 2: The Defense (Predicting the Board's Counter-Argument):**
    * *System Prompt:* "You are corporate counsel defending this pay package. Use DCGK compliance rules to justify these statistical anomalies."
    * *Output Example:* "Defense Prediction: The board will argue the 2.4x 'Reach' is justified by top-quartile ESG target completion, and the 12% base increase was a contractual retention necessity, fully compliant with DCGK Section G."

## 4. The Day 1 Execution Plan (The "One Thing to Do First")
**Friday Morning Protocol:**
1.  **Mikhail & Shivani (Data/Math):** Hand-pick THREE high-profile executives (e.g., VW, Bayer). Force those rows through the join, the regression, and the residual calculation. **Do not attempt to process 3,750 rows until the math is validated on three.**
2.  **Tanmay (Backend/LLM):** Set up the FastAPI server. Write the two adversarial LLM prompt templates that ingest the JSON flags and output the wargaming narratives.
3.  **Saket (UI):** Build the "Wargaming" dashboard. The UI must visualize the "Reach" scatterplot and highlight the specific flags the LLM is reading from.
4.  **Liam (Domain):** Vet the ORBIS variables to ensure they map to ISS guidelines. Write the exact DCGK defense arguments for the LLM's "Defender Mode" prompt.