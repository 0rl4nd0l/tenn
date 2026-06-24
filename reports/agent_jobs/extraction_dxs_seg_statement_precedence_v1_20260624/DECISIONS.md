# Decisions

## Scope Decision

VERIFIED from the source-review board packet and current user instruction:
proceed only with DXS/SEG statement-precedence extractor work.

## Explicit Non-Goals

- ANZ bank metric policy.
- Candidate-review approval.
- Net-debt semantics.
- Broad parser rewrite.
- Global metric mapping.
- Gold fixture, source PDF, prompt, schema, DB, Qdrant, Redis, news, memory,
  model, GPU, runtime, or production-data mutation.

## Duplicate-Work Classification

Final classification: `NO_EXACT_ACTIVE_OR_OPEN_PR_IMPLEMENTATION_FOUND`.
Supporting artifact: `duplicate_work_search.json`.

## Model And Worker Routing

- task_tier: critical
- recommended_model: high reasoning plus focused tests
- actual_model: Codex GPT-5
- why_this_model: Financial Truth extractor behavior must remain source-bound
  and must not absorb ANZ/gold/policy decisions.
- worker_model_allowed: false
- worker_decision_limit: no worker delegation in this slice
- escalation_needed: false after current user approval of the DXS/SEG split

## Closeout Decision

Decision: `DONE_WITH_RISK`.

The scoped DXS/SEG statement-precedence fix is implemented and validated by
focused tests plus the approved-15 no-write replay/scorecard rows. The broader
approved-15 #97 gate remains blocked, so this branch must not be described as a
promotion-ready extraction fix.

## Stop Conditions Honored

- SEG shares outstanding is still missing in the scorecard, but that is not a
  statement-precedence defect and was not fixed in this slice.
- DXS and SEG net-debt rows remain ambiguous/quarantined; net-debt semantics
  were an explicit hard stop.
- BHP/MIN wrong values, RMS cashflow/capex missing rows, GRE/QBE/TCL fail-closed
  rows, and 73 ambiguous quarantines remain outside this scoped DXS/SEG fix.
