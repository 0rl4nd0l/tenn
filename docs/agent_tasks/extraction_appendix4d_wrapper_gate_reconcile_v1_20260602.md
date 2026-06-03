---
job_id: extraction_appendix4d_wrapper_gate_reconcile_v1_20260602
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 5400
output_dir: reports/agent_jobs/extraction_appendix4d_wrapper_gate_reconcile_v1_20260602
mutation_mode: safe_extension
production_data_access: false
allowed_files:
  - docs/agent_tasks/extraction_appendix4d_wrapper_gate_reconcile_v1_20260602.md
  - reports/agent_jobs/extraction_appendix4d_wrapper_gate_reconcile_v1_20260602/README.md
  - reports/agent_jobs/extraction_appendix4d_wrapper_gate_reconcile_v1_20260602/status.json
  - reports/agent_jobs/extraction_appendix4d_wrapper_gate_reconcile_v1_20260602/summary.json
  - reports/agent_jobs/extraction_appendix4d_wrapper_gate_reconcile_v1_20260602/validation.json
  - reports/agent_jobs/extraction_appendix4d_wrapper_gate_reconcile_v1_20260602/diff-check.json
  - reports/agent_jobs/extraction_appendix4d_wrapper_metric_minimum_gate_v1_20260602/README.md
  - reports/agent_jobs/extraction_appendix4d_wrapper_metric_minimum_gate_v1_20260602/status.json
  - reports/agent_jobs/extraction_appendix4d_wrapper_metric_minimum_gate_v1_20260602/summary.json
  - reports/agent_jobs/extraction_appendix4d_wrapper_metric_minimum_gate_v1_20260602/validation.json
  - docs/agent_tasks/extraction_appendix4d_wrapper_gate_to_bounded_validation_v1_20260602.md
  - docs/agent_tasks/extraction_appendix4d_wrapper_metric_minimum_gate_v1_20260602.md
  - reports/agent_jobs/extraction_appendix4d_wrapper_gate_to_bounded_validation_v1_20260602/README.md
  - reports/agent_jobs/extraction_appendix4d_wrapper_gate_to_bounded_validation_v1_20260602/status.json
  - reports/agent_jobs/extraction_appendix4d_wrapper_gate_to_bounded_validation_v1_20260602/diff-check.json
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - financial-engine_v2/backend/tests/test_extraction_capability_guards.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py
  - docs/extraction/metric_extraction_contract.md
  - docs/architecture/12_evaluation_and_drift_monitoring.md
operator_approval_source: User requested Appendix 4D/4E wrapper gate reconciliation on 2026-06-03.
---

# Appendix 4D/4E Wrapper Gate Reconcile V1

## Objective

Reconcile the Appendix 4D/4E wrapper gate into the canonical tree without
broadening the metric ontology or touching unrelated extraction lanes.

## Scope

- Keep the gate exception limited to short Appendix 4D/4E wrapper documents.
- Preserve canonical-only treatment for NTA, dividends/distributions, record
  date, and associates/joint ventures disclosures.
- Preserve the deterministic low-confidence/source-bound bypass.
- Do not change persisted schema, runtime config, prompts, gold labels, or
  broader ontology policy.

## Validation

- Focused pytest on the wrapper gate and ordinary annual/half-year behavior.
- `py_compile` or `ruff` only if touched files require it.
- JSON validation for report artifacts.
- `git diff --check`.
- `scripts/agent_job_contract.py validate`
- `scripts/agent_job_contract.py check-diff`
- No source PDFs staged.
- No broad extraction, backfill, or random sample run.
