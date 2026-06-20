# ProxyEngine — Idea Submission

## One-liner
**ProxyEngine standardizes opaque executive-pay reports and automatically audits them — catching executives who are paid for the size of a much larger company, and proving it with a number.**

## The problem
German executive remuneration is disclosed by law but published in inconsistent, hard-to-compare formats. Worse, the benchmarks used to justify pay are gameable: boards select flattering "peer groups," so almost every CEO looks reasonable relative to the peers their own board picked — the documented "Lake Wobegon" effect, where everyone is above average. Under ARUG II / EU SRD II, shareholders now vote on pay every year ("Say-on-Pay"), but they have no objective, automated way to judge whether a package is actually in line with the market. Both sides feel this: investors lack tooling to audit pay before an AGM, and corporate boards lack a way to test their own packages against proxy-advisor and governance expectations *before* publishing.

## The idea
ProxyEngine is an AI prototype that uses 15 years of German executive-compensation data to (1) **predict expected pay and pay composition** for a firm from its characteristics and performance, (2) **benchmark** actual pay against an *objective, algorithmically defined* peer group, (3) **explain the drivers** of the prediction in plain terms, and (4) **flag governance red flags** — excess pay, weak pay-for-performance alignment, and atypical incentive structures — mapped to German governance law (AktG §§ 87/87a/162, DCGK) and proxy-advisor (ISS/Glass Lewis) logic.

## The core insight (what makes this more than a pay predictor)
**We are not trying to predict pay accurately. We are trying to measure what pay *should* be from legitimate drivers, so that everything unjustified stays visible in the residual — and the residual is the product.** A high-accuracy black-box model would fit the overpayment itself and hide the very thing we want to surface. So we deliberately use a transparent, well-specified baseline (regularized quantile regression, anchored to the well-established firm-size pay elasticity), and read off the gap. We translate that gap into one intuitive number — the **"Reach" ratio**: *"This executive is paid like a firm 2.4× bigger."* Two further flags extend it: an **asymmetric pay-for-luck test** (pay rises with good performance but is shielded from bad), and an **objective peer group** built by enriching industry and clustering on firm economics — removing the board's discretion to hand-pick comparators.

## The differentiator
One engine, two lenses. The *same* objective gap drives a shareholder's "vote-against" case **and** a board's "fix-this-before-you-publish" compliance check. Pay analysis is inherently adversarial, and ProxyEngine serves both sides of that fight from one transparent computation — with a constrained language layer that turns the math into a governance-grounded recommendation and never invents a number it wasn't given.

## Who benefits
- **Asset managers & activist investors** — auditable evidence for how to vote at the AGM.
- **Corporate boards & reporting teams** — a pre-publication stress test against governance and proxy-advisor expectations, plus a standardized, transparent reporting format.
- **Regulators & the public** — a consistent, comparable view of where executive pay is heading.

## Scope for the hackathon
A working prototype on a clean DAX/MDAX subset: real data → expected-pay baseline → Reach residual → red-flag detection → an explainable driver view (gradient-boosted model + SHAP, as the "what drives pay" exhibit) → a simple dashboard with the dual-lens recommendation. Honest about its limits: a prototype, not a finished product — exactly the critical-thinking-first brief the challenge asks for.

---

## If they want a deck, this is the slide order
1. **Hook** — the one-liner + "this CEO is paid like a firm 2.4× bigger."
2. **Problem** — opaque reports + gameable peer groups (Lake Wobegon) + mandatory Say-on-Pay, no objective tool.
3. **Idea** — predict expected pay → benchmark vs objective peers → explain drivers → flag red flags (map to the 4 brief goals).
4. **Insight** — "the residual is the product" + objective peers + the dual-lens (auditor / board) on one engine.
5. **Prototype & who it's for** — DAX subset demo, asset managers + boards, honest scope.
