# Company Analysis Standard

## Scope and Trigger

Apply this standard for ticker-specific deep analysis requests where the user asks for a comprehensive company view, investment-style thesis discussion, or detailed risk/opportunity synthesis.

## Inputs and Evidence Contract

1. Treat backend-provided financial truth as authoritative for numeric claims.
2. Separate confirmed financial truth from narrative/context interpretation.
3. Use peer comparison only when peer evidence exists in the current turn.
4. Do not state unverified values, dates, or events as facts.
5. If evidence is missing, say so explicitly and continue with available confirmed evidence.

## Execution Steps

1. Financial Truth Pass:
Extract and summarize the highest-signal confirmed metrics and facts first.

2. Narrative and Context Pass:
Add business, strategic, and qualitative interpretation clearly labeled as interpretation.

3. Peer Comparison Pass:
Compare with peers only on metrics and observations that are directly available.

4. Strategy-Context Confer:
If strategy criteria are present, state whether evidence supports, conflicts with, or is insufficient for each relevant criterion.

5. Bounded Skeptic Pass:
Include the strongest disconfirming evidence and plausible downside interpretation.

6. Missing-Data Recovery Pass:
List unknowns and what data is missing; avoid backfilling gaps with assumptions.

## Output Contract

Use this top-level section order:

1. `Verdict:`
2. `Evidence:`
3. `Risks:`
4. `Counterpoints:`
5. `Unknowns:`

Inside `Evidence:`, present subsections in this order:

1. Financial truth
2. Narrative/context
3. Peer comparison (if available)
4. Strategy-context confer (if criteria exist)

Every substantive factual line must include user-visible source grounding.

## Memory and Follow-up Rules

1. Thesis-memory proposals must be confirmation-gated.
2. Present proposals as optional recommendations, never as already-committed memory writes.
3. If proposing a memory write, include a short rationale and ask for explicit confirmation.
