---
job_id: extraction_contract_parity_guard_v1_20260526
lane: Financial Truth
supporting_lanes:
  - Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_contract_parity_guard_v1_20260526.md
  - reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/README.md
  - reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/status.json
  - reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/metric_contract_parity_matrix.json
  - reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/diff-check.json
  - reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/validation.json
  - financial-engine_v2/backend/app/models/asx_financials.py
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py
  - financial-engine_v2/backend/app/services/extraction_gold_eval.py
  - financial-engine_v2/backend/app/services/extraction_eval.py
  - financial-engine_v2/backend/app/services/confirmed_metric_coverage_review.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval.py
  - financial-engine_v2/backend/tests/test_extraction_eval.py
  - docs/extraction/metric_extraction_contract.md
  - docs/architecture/12_evaluation_and_drift_monitoring.md
approval_required: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_contract_parity_guard_v1_20260526
mutation_mode: safe_extension
production_data_access: false
allow_unapproved_safe_extension: true
---

# Extraction Contract Parity Guard

## Scope

Implement the next safe issue #98 step: a report-local/test-only metric contract
parity guard that classifies Tenn metric fields across persisted model fields,
active extractor output fields, evaluator-supported fields, confirmed/gold
metric expectation families, planned fields, unsupported fields, and internal
implementation fields.

This job advances Financial Truth readiness by making metric-family support
explicit before broader metric scoring or canonical promotion. It may add
evaluation/reporting helper code and focused synthetic tests only.

## Lane

Primary lane: Financial Truth.

Supporting lane: Evaluation.

## Execution Mode

SAFE EXTENSION, report-local/test-only.

## Session Declaration

Agent: Codex

Worktree: `/home/l4nd0/tenn-extraction-contract-parity-guard-v1-20260526`

Branch: `safe/extraction-contract-parity-guard-v1-20260526`

Issue: #98

Intended files: this task card, a narrow report-local/evaluation parity helper,
focused synthetic unit tests, and this task's report artifacts.

Contested surfaces touched: none.

Collision risk: MEDIUM because this classifies Financial Truth and Evaluation
contracts, but the work is test/report-local and runs in an isolated worktree.

Decision: proceed after task-card validation, shared registry overlap check, and
registry claim.

## Contract Check

Target system layer: Evaluation/reporting around metric-extraction contract
visibility. The guard reads static contract surfaces and emits diagnostics; it
does not alter ingestion, extraction, storage, retrieval, analysis, or client
runtime behavior.

Relevant contract rules: backend remains source of truth; metric extraction must
extract only explicit values and not infer, substitute, or fabricate; no duplicate
production pipeline, parser route, prompt path, canonical write, or datastore
mutation is introduced.

What must not change: production extraction/backfill, production DB writes,
Qdrant/news/memory mutation, canonical financial truth writes, parser routing,
extraction prompts, gold labels, source PDFs, runtime/model/GPU/service config,
Cockpit UI, persisted schema, or canonical extraction metric set.

Why safe: the implementation classifies existing metric-family support and emits
report-local JSON diagnostics. It does not invoke production extraction, mutate
labels, write canonical truth, or change extraction behavior.

GPU process check required: no. This task does not spawn, restart, stop, or
depend on `llama-server`.

## Required Behavior

- Produce a metric parity matrix.
- Explicitly classify at least `revenue`, `operating_cash_flow`, `net_debt`,
  `total_equity`, `interest_expense`, `finance_costs` if present, `cash`,
  `debt/borrowings`, `capex`, `EPS`, `dividends`, and NPAT/profit attributable.
- Use status classes including `supported`, `extractor_supported`,
  `evaluator_supported`, `persisted_only`, `gold_only`, `planned`,
  `internal_only`, `unsupported`, and `ambiguous_requires_policy`.
- Confirm that `total_equity` and `interest_expense` are not silently promoted
  just because persistence has fields for them.
- Emit report-local JSON under
  `reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/`.
- Add tests that fail if persisted-only metrics are treated as extractor-supported
  without explicit contract support.
- Preserve the broad metric goal: many metrics may be supported long term, but
  each metric family must pass source/evaluator/contract gates before canonical
  use.

## Hard Stops

- Stop if implementation requires production extraction or backfill.
- Stop if implementation requires production DB, Qdrant, news, memory, or
  canonical financial truth writes.
- Stop if implementation requires parser routing, extraction prompt, gold-label,
  source-PDF, runtime/model/GPU/service config, or Cockpit UI changes.
- Stop if implementation changes the persisted database schema.
- Stop if implementation adds new metrics to canonical extraction.
- Stop if active registry jobs overlap this job's allowed files.
- Stop if generated diffs escape this allowlist.
- Stop on unrelated cleanup, stash, reset, delete, or source asset mutation.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_contract_parity_guard_v1_20260526.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_contract_parity_guard_v1_20260526.md --repo-root .`
- Focused pytest for touched tests.
- JSON validation for generated artifacts.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_contract_parity_guard_v1_20260526.md`
- `ruff` or `py_compile` when available in the project environment.

## Final Report Requirements

Write
`reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/README.md`
and
`reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/status.json`.

The final report must include branch, HEAD, worktree, task-card path, registry
status, files changed, tests run with exact results, generated artifacts,
Confirmed/Inferred/Speculative/DATA_MISSING, how #98 is advanced, how this
interacts with #97, what remains blocked before broader metric-family scoring,
whether #99 is still required before source reviewability is complete, final git
status, and Project Memory save recommendation.
