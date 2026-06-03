---
job_id: extraction_appendix4d_wrapper_validation_gate_v1_20260602
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
owner: Codex
approval_required: true
allow_unapproved_safe_extension: true
timeout_seconds: 5400
output_dir: reports/agent_jobs/extraction_appendix4d_wrapper_validation_gate_v1_20260602
mutation_mode: safe_extension
production_data_access: false
allowed_files:
  - docs/agent_tasks/extraction_appendix4d_wrapper_validation_gate_v1_20260602.md
  - docs/agent_tasks/extraction_appendix4d_profit_after_tax_alias_v1_20260602.md
  - reports/agent_jobs/extraction_appendix4d_wrapper_validation_gate_v1_20260602/**
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - financial-engine_v2/backend/tests/test_extraction*.py
  - financial-engine_v2/backend/tests/test_extraction_capability_guards.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py
  - docs/extraction/metric_extraction_contract.md
  - docs/architecture/12_evaluation_and_drift_monitoring.md
operator_approval_source: User requested a narrow Appendix 4D/4E wrapper validation gate on 2026-06-03.
---

# Appendix 4D/4E Wrapper Validation Gate V1

## Objective

Add a narrow validation path for short Appendix 4D/4E wrapper documents so they
can pass with two supported canonical metrics only when the required wrapper
disclosures are present as source-bound evidence metadata.

## Scope

- Keep the canonical metric ontology unchanged.
- Do not promote NTA per security, dividends/distributions, or record date to
  canonical metrics.
- Require explicit Appendix 4D/4E wrapper evidence and disclosure metadata for
  the relaxed two-metric path.
- Fail closed when wrapper evidence is missing, ambiguous, or incomplete.

## Target

- GPT Appendix 4D target PDF:
  `/data/asx/docs/GPT/financial_performance/2024-08-19_appendix-4d-gpt-management-holdings-limited_c10a88ab-4290-4395-9521-7f96c50b03c4.pdf`

## Validation

- Focused pytest on the wrapper-gate regression.
- `py_compile` or `ruff` only if touched files require it.
- JSON validation for report artifacts.
- `git diff --check`.
- `scripts/agent_job_contract.py validate`
- `scripts/agent_job_contract.py check-diff`
- No source PDFs staged.
- No broad extraction, backfill, or random sample run.
