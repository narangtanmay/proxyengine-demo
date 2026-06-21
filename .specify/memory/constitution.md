<!--
SYNC IMPACT REPORT
Version: 0.1.0 -> 1.0.0
Modified Principles:
- Set up core financial principles.
Added: NDA Compliance, Deterministic SML, Dual-Lens Separation
Removed: N/A
Templates Requiring Updates: None.
-->

# ProxyEngine Constitution

**Version:** 1.0.0
**Last Amended:** 2026-06-20

## Core Principles

### Principle 1: NDA Compliance & Safe Translation
*   **Rule:** Raw company financial data must never be sent to external generative AI APIs.
*   **Rationale:** Executive compensation data must be processed locally to adhere to strict non-disclosure agreements. Only abstract statistical flags (e.g., Reach ratios) may be passed to the LLM.

### Principle 2: Deterministic SML over Black-Box ML
*   **Rule:** The analytical pipeline must prioritize Statistical Machine Learning (Quantile Regression, Panel Regression) over opaque, non-causal machine learning models like Deep Learning or Random Forests.
*   **Rationale:** Finance professors and proxy advisors demand causal inference, interpretability, and robust standard errors.

### Principle 3: No Hallucination UI Constraints
*   **Rule:** The user interface must not feature an open-ended "chatbot." It must use strict prompt templating restricted to a Dual-Lens framework (Auditor vs. Corporate Defender).
*   **Rationale:** Open-ended queries on financial data risk severe LLM hallucination, which undermines the credibility of the tool.

### Principle 4: Objective Shadow Peers
*   **Rule:** Peer groups must be algorithmically discovered using K-Means on structural fundamentals (asset turnover, risk, efficiency), rather than relying on GICS codes.
*   **Rationale:** Overcomes the "Lake Wobegon" effect where boards manipulate their self-disclosed peer groups.

## Governance
*   **Amendment Procedure:** Any changes to the core rules require a team consensus, especially involving changes to the math layer or external API calls.
*   **Versioning Policy:** Semantic versioning applies. MAJOR version bumps for changes to the econometric formulas.
