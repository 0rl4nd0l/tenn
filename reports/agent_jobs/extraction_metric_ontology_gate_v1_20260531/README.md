# Extraction Metric Ontology Gate

Generated: 2026-05-31T06:27:08Z

This report records the safe-extension slice for the metric extraction handoff:
pre-persistence scorecards now reject unexpected actual payload metrics instead
of silently treating them as successful facts.

## Scope

- Lane: Evaluation, supporting Financial Truth.
- Worktree: `/home/l4nd0/tenn-extraction-metric-ontology-gate-v1-20260531`.
- Branch: `safe/extraction-metric-ontology-gate-v1-20260531`.
- Task card: `docs/agent_tasks/extraction_metric_ontology_gate_v1_20260531.md`.
- Contested surfaces touched: none.

## Behavior Proven

- `interest_expense` is visible to the ontology bridge as a supplemental,
  non-extractor-target, non-collapse-safe family.
- `finance_costs` remains unsupported without explicit policy.
- `total_debt` remains an internal-only alias, not a successful extracted fact.
- Persisted-only, internal-only, planned, ambiguous, and unsupported metric
  families cannot pass the pre-persistence scorecard as successful facts.
- Unexpected supported actual-payload metrics fail the gate unless fixture
  expectations explicitly cover them.
- Report-local gates still keep `canonical_write_allowed=false` and
  `broad_backfill_authorized=false`.

## Boundaries

No backend, worker, llama, canary, runtime extraction, backfill, DB, Qdrant,
source-PDF, parser, prompt, schema, model/GPU config, Cockpit UI, GitHub, or
canonical-truth mutation was performed.

## Validation

- Task card validation passed.
- Registry active-job inspection showed only this active Evaluation claim plus
  an unrelated stale Query Orchestration claim.
- Focused Python compile passed for touched scorecard, ontology, and test files.
- Focused pytest passed: `61 passed, 1 warning`.
- Targeted Ruff passed.
- `git diff --check` passed.
- Raw PDF/archive/database/parquet/CSV change scan found no changed paths.
- Task-card diff checks passed for both the preserved WIP implementation diff
  and this final report/state closeout diff.

## Remaining Blockers

- Third canary execution still requires explicit approval and a fresh runtime
  preflight.
- Full accurate extraction graduation remains unproven by this evaluation-only
  slice.
