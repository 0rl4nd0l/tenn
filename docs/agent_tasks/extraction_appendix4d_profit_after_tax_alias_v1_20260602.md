---
job_id: extraction_appendix4d_profit_after_tax_alias_v1_20260602
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 5400
output_dir: reports/agent_jobs/extraction_appendix4d_profit_after_tax_alias_v1_20260602
mutation_mode: safe_extension
production_data_access: false
allowed_files:
  - docs/agent_tasks/extraction_appendix4d_profit_after_tax_alias_v1_20260602.md
  - reports/agent_jobs/extraction_appendix4d_profit_after_tax_alias_v1_20260602/**
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - financial-engine_v2/backend/tests/test_extraction*.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py
  - docs/extraction/metric_extraction_contract.md
  - docs/architecture/12_evaluation_and_drift_monitoring.md
operator_approval_source: User requested narrow Appendix 4D/4E profit-after-tax alias support on 2026-06-03.
---

# Appendix 4D/4E Profit-After-Tax Alias Support V1

## Objective

Add a narrow, source-bound alias path for Appendix 4D/4E profit-after-tax row
variants so the GPT Appendix 4D blocker can be retested without broadening the
canonical metric ontology.

## Scope

- Keep the change limited to existing `np_attributable` handling.
- Accept explicit profit-after-tax row variants such as the Appendix 4D
  ordinary-activities NPAT row when they are the best source-bound evidence.
- Do not promote `nta_per_security`, dividends, distributions, or record-date
  rows into canonical metric families.
- Do not change persisted schema, runtime config, prompts, gold labels, or
  broader ontology policy.

## Target

- PDF:
  `/data/asx/docs/GPT/financial_performance/2024-08-19_appendix-4d-gpt-management-holdings-limited_c10a88ab-4290-4395-9521-7f96c50b03c4.pdf`

## Validation

- Focused pytest on the Appendix 4D alias regression.
- `py_compile` or `ruff` only if touched files require it.
- JSON validation for report artifacts.
- `git diff --check`.
- `scripts/agent_job_contract.py validate`
- `scripts/agent_job_contract.py check-diff`
- No source PDFs staged.
- No broad extraction, backfill, or random sample run.
