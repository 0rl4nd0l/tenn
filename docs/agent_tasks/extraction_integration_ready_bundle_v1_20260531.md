---
job_id: extraction_integration_ready_bundle_v1_20260531
lane: Evaluation
supporting_lanes:
  - Financial Truth
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_integration_ready_bundle_v1_20260531.md
  - docs/agent_tasks/extraction_goal_proof_matrix_refresh_v3_20260531.md
  - docs/agent_tasks/extraction_metric_ontology_gate_v1_20260531.md
  - docs/agent_tasks/extraction_runtime_approval_preflight_v1_20260531.md
  - docs/agent_tasks/extraction_synced_eval_verification_v1_20260531.md
  - docs/agent_tasks/extraction_third_canary_runtime_execution_v1_20260531.md
  - docs/claude/STATE.md
  - docs/extraction/metric_extraction_contract.md
  - financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py
  - financial-engine_v2/backend/app/services/metric_ontology_bridge.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py
  - financial-engine_v2/backend/tests/test_metric_ontology_bridge.py
  - reports/agent_jobs/extraction_goal_proof_matrix_refresh_v3_20260531/README.md
  - reports/agent_jobs/extraction_goal_proof_matrix_refresh_v3_20260531/diff-check.json
  - reports/agent_jobs/extraction_goal_proof_matrix_refresh_v3_20260531/objective_matrix.json
  - reports/agent_jobs/extraction_goal_proof_matrix_refresh_v3_20260531/status.json
  - reports/agent_jobs/extraction_goal_proof_matrix_refresh_v3_20260531/validation.json
  - reports/agent_jobs/extraction_integration_ready_bundle_v1_20260531/README.md
  - reports/agent_jobs/extraction_integration_ready_bundle_v1_20260531/status.json
  - reports/agent_jobs/extraction_integration_ready_bundle_v1_20260531/validation.json
  - reports/agent_jobs/extraction_integration_ready_bundle_v1_20260531/diff-check.json
  - reports/agent_jobs/extraction_metric_ontology_gate_v1_20260531/README.md
  - reports/agent_jobs/extraction_metric_ontology_gate_v1_20260531/diff-check.json
  - reports/agent_jobs/extraction_metric_ontology_gate_v1_20260531/status.json
  - reports/agent_jobs/extraction_metric_ontology_gate_v1_20260531/validation.json
  - reports/agent_jobs/extraction_runtime_approval_preflight_v1_20260531/README.md
  - reports/agent_jobs/extraction_runtime_approval_preflight_v1_20260531/diff-check.json
  - reports/agent_jobs/extraction_runtime_approval_preflight_v1_20260531/runtime_preflight.json
  - reports/agent_jobs/extraction_runtime_approval_preflight_v1_20260531/status.json
  - reports/agent_jobs/extraction_runtime_approval_preflight_v1_20260531/validation.json
  - reports/agent_jobs/extraction_synced_eval_verification_v1_20260531/README.md
  - reports/agent_jobs/extraction_synced_eval_verification_v1_20260531/diff-check.json
  - reports/agent_jobs/extraction_synced_eval_verification_v1_20260531/status.json
  - reports/agent_jobs/extraction_synced_eval_verification_v1_20260531/validation.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_integration_ready_bundle_v1_20260531
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: none
related_issue: 97
---

# Extraction Integration Ready Bundle

## Objective

Create a clean integration branch from
`origin/migration/clean-runtime-baseline-reconstruct-v1` that preserves the
current metric ontology gate, synced eval verification, runtime approval
preflight, and refreshed proof matrix content from
`safe/extraction-metric-ontology-gate-v1-20260531` without carrying its WIP
history.

## Session Declaration

- Agent: Codex.
- Worktree:
  `/home/l4nd0/tenn-extraction-integration-ready-v1-20260531`.
- Branch: `integrate/extraction-metric-ontology-gate-v1-20260531`.
- Intended files: all files listed in `allowed_files`.
- Contested surfaces touched: none.
- Collision risk: LOW; new isolated worktree from origin baseline.
- Decision: proceed after validation, overlap check, and claim.

## Contract Check

- Target system layer: Evaluation tooling and report artifacts, supporting
  Financial Truth.
- Relevant contract rules: backend remains authoritative; extraction must not
  infer/substitute metrics; report-local scorecards do not authorize writes.
- What must not change: runtime services, source PDFs, DB/Qdrant, parser
  routing, prompts, schemas, Cockpit UI, GitHub state, and canonical write
  permission.
- Why safe: this is a clean integration branch of already validated local
  changes plus validation/report artifacts. It does not run runtime extraction.
- GPU process check required: no process is spawned or restarted.

## Validation

- Validate this task card.
- Check registry overlap and claim.
- Apply the content diff from `safe/extraction-metric-ontology-gate-v1-20260531`.
- Compare final tree content against the source branch for the carried files.
- Run focused extraction scorecard/ontology tests.
- Run broader extraction evaluation lane.
- Validate JSON report artifacts.
- Run raw binary/database artifact scan.
- Run `git diff --check`.
- Run task-card `check-diff`.
- Release registry claim.

## Forbidden

- Shared baseline mutation.
- Runtime startup/reload, canary execution, document submission, backfill.
- DB/Qdrant/source-PDF/canonical-truth mutation.
- Parser, prompt, schema, Cockpit UI, GitHub, or model/GPU config mutation.
