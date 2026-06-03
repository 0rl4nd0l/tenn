---
job_id: extraction_appendix4d_wrapper_gate_to_bounded_validation_v1_20260602
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Query Orchestration
  - Provenance
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 10800
output_dir: reports/agent_jobs/extraction_appendix4d_wrapper_gate_to_bounded_validation_v1_20260602
mutation_mode: safe_extension
production_data_access: false
allowed_files:
  - docs/agent_tasks/extraction_appendix4d_wrapper_gate_to_bounded_validation_v1_20260602.md
  - docs/agent_tasks/extraction_appendix4d_wrapper_gate_reconcile_v1_20260602.md
  - docs/agent_tasks/extraction_appendix4d_wrapper_metric_minimum_gate_v1_20260602.md
  - reports/agent_jobs/extraction_appendix4d_wrapper_gate_reconcile_v1_20260602/README.md
  - reports/agent_jobs/extraction_appendix4d_wrapper_gate_reconcile_v1_20260602/status.json
  - reports/agent_jobs/extraction_appendix4d_wrapper_gate_reconcile_v1_20260602/summary.json
  - reports/agent_jobs/extraction_appendix4d_wrapper_gate_reconcile_v1_20260602/validation.json
  - reports/agent_jobs/extraction_appendix4d_wrapper_gate_reconcile_v1_20260602/diff-check.json
  - reports/agent_jobs/extraction_appendix4d_wrapper_gate_to_bounded_validation_v1_20260602/README.md
  - reports/agent_jobs/extraction_appendix4d_wrapper_gate_to_bounded_validation_v1_20260602/status.json
  - reports/agent_jobs/extraction_appendix4d_wrapper_gate_to_bounded_validation_v1_20260602/diff-check.json
  - reports/agent_jobs/extraction_appendix4d_wrapper_metric_minimum_gate_v1_20260602/README.md
  - reports/agent_jobs/extraction_appendix4d_wrapper_metric_minimum_gate_v1_20260602/status.json
  - reports/agent_jobs/extraction_appendix4d_wrapper_metric_minimum_gate_v1_20260602/summary.json
  - reports/agent_jobs/extraction_appendix4d_wrapper_metric_minimum_gate_v1_20260602/validation.json
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - financial-engine_v2/backend/tests/test_extraction_capability_guards.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py
  - docs/extraction/metric_extraction_contract.md
  - docs/architecture/12_evaluation_and_drift_monitoring.md
operator_approval_source: User requested bounded conditional progress on Appendix 4D wrapper validation on 2026-06-03.
---

# Appendix 4D Wrapper Gate To Bounded Validation

## Objective

Continue Appendix 4D broad-accuracy progress through the next safe conditional
phases: reconcile the wrapper gate, validate the GPT Appendix 4D target, then
run exactly one bounded count-16 validation sample only if prior gates pass.

## Scope

- Keep the work confined to the Appendix 4D/4E wrapper gate and bounded
  validation artifacts.
- Do not run broad extraction, broad backfill, or full ticker-universe
  extraction.
- Do not mutate source PDFs, prompts, gold labels, runtime/model/GPU config, or
  database/Qdrant/news state beyond bounded validation behavior.

## Validation

- Phase-specific focused pytest and `py_compile`.
- JSON validation for report artifacts.
- `git diff --check`.
- `scripts/agent_job_contract.py validate`
- `scripts/agent_job_contract.py check-diff`
- No source PDFs staged.
- Final `git status` clean for the touched worktree.
