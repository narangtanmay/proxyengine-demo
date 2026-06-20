# ProxyEngine — Purpose-Driven Architecture Sketch (FOR TEAM SIGN-OFF, NOT YET IN THE PLAYBOOK)

> Source: `Scanned_20260620_091609.pdf` (whiteboard sketch). This replaces the passive "Dual-Lens Toggle" (static `ProxyEngine_Group_Share_Document.md` §4) with an **active, purpose-driven query flow**. Nothing in the existing MDs is changed yet — this is the proposal to review before we write it in.

---

## 1. What changes, in one sentence

Instead of the user flipping a toggle between two pre-written narrative lenses, **the user states their intent up front** ("I'm building a short case" / "I'm auditing before publication" / "I need the statutory check"), the system runs only the checks that intent requires, and the LLM answers **the specific questions tied to that intent** — grounded in a machine-checkable evidence object, not a free narrative.

```
User picks PURPOSE
      │
      ▼
Purpose → Question Matrix (which checks apply?)
      │
      ▼
Decision Model (DM) — runs quantile regression, K-Means, legal checks
      │
      ▼
EvidenceTrace (strict, typed, numeric — no prose yet)
      │
      ▼
LLM Synthesis — bullet answer per question, each bullet cites an EvidenceTrace field
      │
      ▼
UI renders: Question → Bullet Answer → (expand) → raw evidence it came from
```

The old Dual-Lens toggle becomes a **special case**: "Build an activist case" and "Pre-publication board audit" are now two entries in the Purpose enum, asking different subsets of the same question matrix. We lose nothing from §4 — we generalize it.

---

## 2. Purpose enum and the Question Matrix

### 2.1 `Purpose` (Pydantic enum)

```python
class Purpose(str, Enum):
    ACTIVIST_CASE = "activist_case"        # "Build an activist short case"
    BOARD_AUDIT = "board_audit"            # "Pre-publication board audit"
    LEGAL_CHECK = "legal_check"            # "Statutory legal check only"
```

Three, not five — keep the matrix small enough to demo. Each maps to an ordered list of questions. This *is* the generalization of the old two narrative lenses, plus a third, narrower lens for the technical judge (pure §87/§87a AktG compliance, no editorializing).

### 2.2 The matrix (purpose → questions → required evidence)

| # | Question (shown to user) | Required `EvidenceTrace` fields | Statute / method | Asked for |
|---|---|---|---|---|
| Q1 | "How much bigger is this CEO's pay than their firm's size justifies?" | `residual`, `beta`, `reach` | Quantile regression | ACTIVIST_CASE, BOARD_AUDIT |
| Q2 | "Who are the objective peers, and how does pay compare to them?" | `peer_cluster_id`, `peer_cluster_members`, `peer_median_pay` | K-Means + industry enrichment | ACTIVIST_CASE, BOARD_AUDIT |
| Q3 | "Does LTI outweigh STI, as §87 AktG requires?" | `lti_sti_ratio`, `lti_sti_breach` | §87 AktG | ALL THREE |
| Q4 | "Was pay reduced when performance fell, as §87 AktG's downturn duty requires?" | `pay_luck_beta_up`, `pay_luck_beta_down`, `downturn_duty_breach` | §87 AktG + Bertrand & Mullainathan | ACTIVIST_CASE, LEGAL_CHECK |
| Q5 | "Is the max-compensation cap and performance metric disclosed, per §87a AktG?" | `disclosure_compliant`, `opting_out` | §87a AktG | BOARD_AUDIT, LEGAL_CHECK |
| Q6 | "Has this executive carried an unexplained premium across employers?" | `cross_firm_premium`, `cross_firm_years` | exec_id panel (stretch) | ACTIVIST_CASE (only if stretch flag built) |

`Purpose → [QuestionIDs]` is a static lookup table, not logic scattered through the backend:

```python
PURPOSE_QUESTION_MATRIX: dict[Purpose, list[str]] = {
    Purpose.ACTIVIST_CASE: ["Q1", "Q2", "Q3", "Q4", "Q6"],
    Purpose.BOARD_AUDIT:   ["Q1", "Q2", "Q3", "Q5"],
    Purpose.LEGAL_CHECK:   ["Q3", "Q4", "Q5"],
}
```

This table is the cheapest, highest-leverage artifact in this whole redesign — it's literally a dict, and it's the thing that makes the UI, the DM, and the LLM all agree on what's being asked.

---

## 3. `EvidenceTrace` — the strict object between DM and LLM

This is the contract that makes the "never hallucinates a number" claim in §4/§6 of the old doc actually enforceable, instead of just asserted. The LLM is never shown raw data — only this object.

```python
class EvidenceTrace(BaseModel):
    isin: str
    year: int
    exec_id: str

    # Q1 — baseline / Reach
    residual: float                     # log-pay residual from quantile regression
    beta: float                         # size elasticity, expected ~0.3
    reach: float                        # exp(residual / beta)

    # Q2 — peer group
    peer_cluster_id: int
    peer_cluster_members: list[str]     # ISINs in the same cluster
    peer_median_pay: float

    # Q3 — LTI/STI (cheapest, highest-confidence flag — build first)
    lti_sti_ratio: float                # multi_year_bonus_grants / one_year_bonus
    lti_sti_breach: bool

    # Q4 — pay-for-luck / downturn duty
    pay_luck_beta_up: float | None      # null if regression not run for this purpose
    pay_luck_beta_down: float | None
    downturn_duty_breach: bool | None

    # Q5 — disclosure
    opting_out: bool
    disclosure_compliant: bool

    # Q6 — stretch
    cross_firm_premium: float | None
    cross_firm_years: list[int] | None

    # meta — for the "show your work" panel and Q&A safety
    data_completeness_warning: str | None   # e.g. "2021 missing; flag uses 2020/2022 only"
    computed_at: datetime
```

Rules (carried over unchanged from the old §4/§6 anti-hallucination constraint, just now enforced on a typed object instead of a prose payload):
- Fields irrelevant to the selected `Purpose` are `null`, not omitted — the LLM prompt can say "if a field is null, do not answer that question."
- Every number the LLM is allowed to say out loud exists as a named field here. No new arithmetic happens inside the prompt.
- This object is what gets logged for the reproducibility/audit trail already promised in §6.

---

## 4. API shape (FastAPI)

Two endpoints, not one — separating "compute the evidence" from "write the answer" is what lets the UI show the raw evidence panel *before* the prose, which is the credibility moment for finance judges ("here's the number, here's the sentence we built from it").

```
POST /analyze
  body: { isin: str, year: int, purpose: Purpose }
  → resolves exec_id(s) for that isin/year internally
  → returns: { request_id: str, evidence_trace: EvidenceTrace, questions: list[QuestionID] }

POST /synthesize
  body: { request_id: str }   # looks up the cached EvidenceTrace + purpose + question list
  → returns: { answers: list[{ question_id, question_text, bullets: list[str] }] }
```

```python
class AnalyzeRequest(BaseModel):
    isin: str
    year: int
    purpose: Purpose

class AnalyzeResponse(BaseModel):
    request_id: str
    evidence_trace: EvidenceTrace
    questions: list[str]            # question IDs from the matrix, in order

class SynthesizeRequest(BaseModel):
    request_id: str

class AnsweredQuestion(BaseModel):
    question_id: str
    question_text: str
    bullets: list[str]              # each bullet must cite a field name from EvidenceTrace

class SynthesizeResponse(BaseModel):
    answers: list[AnsweredQuestion]
```

Why split into two calls instead of one `/analyze-and-explain`: it's the same reason Step 4 in the old doc already separated "compute flags" from "render narrative" — but now it's visible at the API boundary, not just an internal implementation detail. It also means a future judge-facing "raw evidence" toggle is just "don't call `/synthesize`," not new code.

---

## 5. Synthesis layer — prompt template skeleton

```text
SYSTEM:
You are a compliance/governance assistant. You answer ONLY the questions listed below.
You may use ONLY the numeric fields given in EVIDENCE. If a field is null, say the
check was not run for this purpose — do not guess or compute a substitute number.
Every bullet must be traceable to one or more named EVIDENCE fields.
Output format: one bullet per question, in the order given.

QUESTIONS:
{{ for each question_id in questions }}
  - {{question_text}}  [cites: {{required_evidence_fields}}]

EVIDENCE:
{{ EvidenceTrace as JSON, non-null fields only }}

USER PURPOSE: {{ purpose }}
(Use this only to set tone: ACTIVIST_CASE = adversarial/voting framing,
BOARD_AUDIT = compliance-fix framing, LEGAL_CHECK = neutral statutory framing.
Purpose changes TONE, never which facts you're allowed to state.)
```

This is the cleanest way to keep the old §4 "one engine, two lenses" insight: `purpose` still only ever touches *tone* via the system prompt, exactly like the Dual-Lens toggle did — it just now also controls *which questions get asked*, which is the genuinely new piece from the sketch.

---

## 6. Frontend — state machine replacing the toggle

```
IDLE
  └─ user selects Purpose ──────────────▶ PURPOSE_SELECTED
PURPOSE_SELECTED
  └─ POST /analyze ─────────────────────▶ EVIDENCE_LOADING
EVIDENCE_LOADING
  └─ response received ─────────────────▶ EVIDENCE_READY
       (render: evidence panel with raw residual/beta/reach/booleans,
        question checklist appears, each item shows ⏳)
EVIDENCE_READY
  └─ POST /synthesize ──────────────────▶ ANSWER_LOADING
ANSWER_LOADING
  └─ response received ─────────────────▶ ANSWER_READY
       (each question's ⏳ becomes a bullet answer; clicking a bullet
        highlights the EvidenceTrace field(s) it cites)
ANSWER_READY
  └─ user changes Purpose ──────────────▶ PURPOSE_SELECTED (re-run)
```

This is still "cheap to build — two system prompts over one backend" in spirit (old §4 closing line), just: 3 purposes instead of 2 prompts, and a visible evidence panel as a new, free demo asset (judges get to watch the raw numbers appear before the prose — this is arguably a *stronger* "wow moment" than the toggle was, not a more expensive one).

---

## 7. What this does NOT change

- Step 1 (peer groups), Step 2 (quantile regression baseline + why parsimonious is correct), Step 3's flag definitions (§87/§87a grounding) — all unchanged. This sketch only changes *how the user asks for them and how the answer is assembled*, not what's computed.
- Day 1 plan, cut order, and the JSON-contract-first sequencing in §5 of the old doc are unaffected — `EvidenceTrace` simply replaces the old ad hoc "JSON payload" with a typed version of the same fields.
- The risk/ethics section (§6) carries over unchanged — pseudonymization and "flags not verdicts" framing applies identically here.

---

## 8. Open questions for the team before this goes into the MD

1. **Scope for Day 1/2:** do we build all 6 questions, or demo with Q1/Q2/Q3 only (the ones with confirmed columns) and mark Q4/Q5/Q6 as "purpose supported, evidence pending" in the UI? *(Recommendation: Q1–Q3 real, Q4 real if pay-for-luck regression lands, Q5/Q6 stubbed with `null` fields — the schema already supports this gracefully.)*
2. **Single isin/year per request, or batch?** Sketch implies one exec/firm at a time (matches the 3-firm Day-1 demo scope). Confirm we're not promising portfolio-level batch analysis we won't have time to build.
3. **Does `/analyze` and `/synthesize` being two calls cost us demo time/complexity** versus one combined endpoint? *(Recommendation: keep them separate — the evidence-then-prose reveal is a UX asset, and FastAPI cost of two routes over one is negligible.)*
4. **Who owns the Question Matrix content** (the exact wording of Q1–Q6 and which statute they cite) — this reads like Liam's domain lane, same as the old DCGK/threshold-writing task in §5 step 5.

---

**Once the team signs off on sections 2–6 above, this gets folded into `ProxyEngine_Group_Share_Document.md` §3–5, replacing the Dual-Lens Toggle section, and a short addition to `ProxyEngine_Idea_Submission.md`'s "idea" paragraph to mention purpose-driven Q&A instead of just a dashboard.**
