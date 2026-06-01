---
job_id: extraction_integrate_prepersistence_hardening_stack_v1_20260601
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_integrate_prepersistence_hardening_stack_v1_20260601.md
  - docs/agent_tasks/extraction_metric_ontology_prepersistence_gate_v1_20260531.md
  - docs/agent_tasks/extraction_payload_actuals_coverage_gate_v1_20260531.md
  - docs/agent_tasks/extraction_payload_gate_blocking_summary_v1_20260531.md
  - docs/agent_tasks/extraction_payload_scorecard_cli_gate_v1_20260531.md
  - docs/agent_tasks/extraction_storage_metric_contract_gate_v1_20260531.md
  - docs/claude/STATE.md
  - docs/extraction/metric_extraction_contract.md
  - financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py
  - financial-engine_v2/backend/app/services/pipeline.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py
  - financial-engine_v2/backend/tests/test_pipeline_stages.py
  - reports/agent_jobs/extraction_integrate_prepersistence_hardening_stack_v1_20260601/README.md
  - reports/agent_jobs/extraction_integrate_prepersistence_hardening_stack_v1_20260601/status.json
  - reports/agent_jobs/extraction_integrate_prepersistence_hardening_stack_v1_20260601/validation.json
  - reports/agent_jobs/extraction_integrate_prepersistence_hardening_stack_v1_20260601/diff-check.json
  - reports/agent_jobs/extraction_metric_ontology_prepersistence_gate_v1_20260531/README.md
  - reports/agent_jobs/extraction_metric_ontology_prepersistence_gate_v1_20260531/diff-check.json
  - reports/agent_jobs/extraction_metric_ontology_prepersistence_gate_v1_20260531/function_quality_findings.json
  - reports/agent_jobs/extraction_metric_ontology_prepersistence_gate_v1_20260531/status.json
  - reports/agent_jobs/extraction_metric_ontology_prepersistence_gate_v1_20260531/validation.json
  - reports/agent_jobs/extraction_payload_actuals_coverage_gate_v1_20260531/README.md
  - reports/agent_jobs/extraction_payload_actuals_coverage_gate_v1_20260531/diff-check.json
  - reports/agent_jobs/extraction_payload_actuals_coverage_gate_v1_20260531/function_quality_findings.json
  - reports/agent_jobs/extraction_payload_actuals_coverage_gate_v1_20260531/status.json
  - reports/agent_jobs/extraction_payload_actuals_coverage_gate_v1_20260531/validation.json
  - reports/agent_jobs/extraction_payload_gate_blocking_summary_v1_20260531/README.md
  - reports/agent_jobs/extraction_payload_gate_blocking_summary_v1_20260531/diff-check.json
  - reports/agent_jobs/extraction_payload_gate_blocking_summary_v1_20260531/function_quality_findings.json
  - reports/agent_jobs/extraction_payload_gate_blocking_summary_v1_20260531/gate_actionability_sample.json
  - reports/agent_jobs/extraction_payload_gate_blocking_summary_v1_20260531/status.json
  - reports/agent_jobs/extraction_payload_gate_blocking_summary_v1_20260531/validation.json
  - reports/agent_jobs/extraction_payload_scorecard_cli_gate_v1_20260531/README.md
  - reports/agent_jobs/extraction_payload_scorecard_cli_gate_v1_20260531/cli_actuals_sample.json
  - reports/agent_jobs/extraction_payload_scorecard_cli_gate_v1_20260531/cli_payload_gate_sample.json
  - reports/agent_jobs/extraction_payload_scorecard_cli_gate_v1_20260531/diff-check.json
  - reports/agent_jobs/extraction_payload_scorecard_cli_gate_v1_20260531/function_quality_findings.json
  - reports/agent_jobs/extraction_payload_scorecard_cli_gate_v1_20260531/status.json
  - reports/agent_jobs/extraction_payload_scorecard_cli_gate_v1_20260531/validation.json
  - reports/agent_jobs/extraction_storage_metric_contract_gate_v1_20260531/README.md
  - reports/agent_jobs/extraction_storage_metric_contract_gate_v1_20260531/diff-check.json
  - reports/agent_jobs/extraction_storage_metric_contract_gate_v1_20260531/function_quality_findings.json
  - reports/agent_jobs/extraction_storage_metric_contract_gate_v1_20260531/status.json
  - reports/agent_jobs/extraction_storage_metric_contract_gate_v1_20260531/validation.json
  - scripts/extraction_gold_eval_scorecard.py
  - scripts/test_extraction_gold_eval_scorecard.py
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_integrate_prepersistence_hardening_stack_v1_20260601
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: none
operator_approval_source: "User replied Proceed after runtime status update on 2026-06-01; prior approvals authorized full runtime work needed for the extraction goal."
---

# Extraction Integrate Prepersistence Hardening Stack V1

## Objective

Integrate the already-validated extraction hardening stack onto
`migration/clean-runtime-baseline-reconstruct-v1` before runtime canary
execution, so the canary proves the current pre-persistence gates and storage
metric contract rather than a stale baseline.

## Session Declaration

Agent: Codex

Branch: `migration/clean-runtime-baseline-reconstruct-v1`

Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`

Lane: Financial Truth

Execution mode: SAFE EXTENSION

Intended files: this task card, the five completed extraction hardening task
cards/report bundles, extraction scorecard/pipeline code and focused tests,
the metric extraction contract doc, and `docs/claude/STATE.md`.

Contested surfaces touched: none from the explicit contested-surface list.

Collision risk: HIGH because the merged stack touches financial-truth
extraction/storage behavior. Proceed only after registry evidence shows no
overlapping extraction/backfill/runtime job.

Decision: proceed after validation, overlap check, registry claim, clean
merge-conflict preflight, focused validation, check-diff, and claim release.

## Contract Check

Target system layers: Extraction, Storage, Evaluation, and Provenance.

Relevant contract rules: backend remains the sole authority; metric extraction
must use explicit values only; normalization may not infer, substitute, or fill
gaps; canonical storage must fail closed on unsupported metric families.

What must not change: source PDFs, DB schema/migrations, parser routing,
runtime/model/GPU config, Qdrant/news/memory stores, Cockpit UI, broad
backfill, and direct datastore mutation.

Why safe: this task only integrates previously validated commits that tighten
pre-persistence scorecard gates and storage metric allowlists before the
runtime canary. It does not run extraction, backfill, or direct datastore
mutation.

GPU process check required: no for the integration itself. The next runtime
canary task must run `scripts/gpu_process_guard.sh --check` immediately before
backend/worker execution.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_integrate_prepersistence_hardening_stack_v1_20260601.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_integrate_prepersistence_hardening_stack_v1_20260601.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_integrate_prepersistence_hardening_stack_v1_20260601.md --repo-root .`
- Merge-conflict preflight against `safe/extraction-payload-actuals-coverage-gate-v1-20260531`.
- Focused pytest/ruff gates for the integrated extraction stack.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_integrate_prepersistence_hardening_stack_v1_20260601.md --repo-root .`
- Registry release and final list-active.

## Hard Stops

- Do not run the third canary under this card.
- Do not call `POST /api/process/document/{document_id}`.
- Do not start/reload backend, worker, or GPU worker under this card.
- Do not perform direct SQL, broad backfill, Qdrant/news/memory writes, source
  PDF mutation, prompt/parser routing changes, schema changes, or GitHub
  mutation.
