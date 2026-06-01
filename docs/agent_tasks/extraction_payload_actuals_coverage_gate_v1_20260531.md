---
job_id: extraction_payload_actuals_coverage_gate_v1_20260531
lane: Financial Truth
supporting_lanes:
  - Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_payload_actuals_coverage_gate_v1_20260531.md
  - reports/agent_jobs/extraction_payload_actuals_coverage_gate_v1_20260531/README.md
  - reports/agent_jobs/extraction_payload_actuals_coverage_gate_v1_20260531/status.json
  - reports/agent_jobs/extraction_payload_actuals_coverage_gate_v1_20260531/validation.json
  - reports/agent_jobs/extraction_payload_actuals_coverage_gate_v1_20260531/function_quality_findings.json
  - reports/agent_jobs/extraction_payload_actuals_coverage_gate_v1_20260531/diff-check.json
  - financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py
  - scripts/test_extraction_gold_eval_scorecard.py
  - docs/extraction/metric_extraction_contract.md
  - docs/claude/STATE.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_payload_actuals_coverage_gate_v1_20260531
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: none
---

# Extraction Payload Actuals Coverage Gate V1

## Objective

Harden the report-local confirmed-metric payload scorecard so pre-persistence
gate artifacts fail closed when the supplied actual payload map contains
documents that are outside the scorecard fixture scope.

This closes an evaluation-boundary gap before any canary promotion decision:
every supplied actual extraction payload must either be matched to a fixture
document or be explicitly blocking as unmatched. Extra actuals must not be
silently ignored.

## Session Declaration

- Agent: Codex.
- Worktree:
  `/home/l4nd0/tenn-extraction-payload-actuals-coverage-gate-v1-20260531`.
- Branch: `safe/extraction-payload-actuals-coverage-gate-v1-20260531`.
- Base: `safe/extraction-storage-metric-contract-gate-v1-20260531` at
  `b3c6ae08`.
- Intended files: only this task card, the report bundle, the scorecard helper,
  focused tests, metric contract docs, and `docs/claude/STATE.md`.
- Contested surfaces touched: none from the AGENTS.md contested list.
- Collision risk: MEDIUM/HIGH by Financial Truth semantics, resolved by
  isolated worktree, active-registry non-overlap, and exact allowlist.
- Decision: proceed in SAFE EXTENSION MODE after validation and claim.

## Contract Check

- Target system layer: Evaluation/pre-persistence truth gate around backend
  extraction payloads.
- Relevant rules: backend-owned financial truth must be explicit and
  source-bound; evaluation artifacts must fail closed instead of silently
  ignoring unreviewed extraction outputs.
- What must not change: runtime services, canary execution, parser routing,
  prompts, schema migrations, source PDFs, Qdrant, embeddings, Cockpit UI,
  GitHub state, or production data stores.
- Why safe: the change only adds deterministic scorecard/gate diagnostics for
  operator-supplied actual payload maps. It does not run extraction, mutate
  stores, or authorize canonical writes.
- GPU process check required: no. This task does not start, restart, or depend
  on llama-server.

## Required Implementation

- Track which actual payload document keys match the fixture set.
- Report unmatched actual payload ids/counts in the payload scorecard.
- Block the pre-persistence gate when unmatched actual payloads are present.
- Preserve existing missing-actual, wrong-value, wrong-period, wrong-scale,
  missing-evidence, unsupported, and ambiguous behavior.
- Add focused tests proving extra/unmatched actuals fail the gate.

## Forbidden

- Runtime backend startup, route submission, canary execution, broad backfill,
  direct SQL, source-PDF mutation, parser/prompt/schema changes, Qdrant or
  embedding writes, Cockpit UI changes, GitHub mutation, service restart, and
  schema migration.

## Required Validation

- Task card validation and registry claim.
- Focused pytest for scorecard service tests.
- Focused script pytest if CLI-facing behavior changes.
- Targeted Ruff for touched Python files.
- `py_compile` for touched Python files.
- `python3 scripts/agent_job_contract.py check-diff <this card>`.
- `git diff --cached --check`.
- Registry release.
