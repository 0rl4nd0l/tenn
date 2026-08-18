---
job_id: extraction_accounting_number_parse_v1_20260616
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_accounting_number_parse_v1_20260616.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - reports/agent_jobs/extraction_accounting_number_parse_v1_20260616/README.md
  - reports/agent_jobs/extraction_accounting_number_parse_v1_20260616/status.json
  - reports/agent_jobs/extraction_accounting_number_parse_v1_20260616/validation.json
  - reports/agent_jobs/extraction_accounting_number_parse_v1_20260616/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_accounting_number_parse_v1_20260616
mutation_mode: safe_extension
allow_audit_code_changes: true
production_data_access: false
github_mutation_allowed: true
---

# Extraction Accounting Number Parse

## Objective

Implement one bounded #286 safe extension: deterministically parse common
accounting number formats emitted by pass3a before reconciliation.

## Current Evidence

- Issue #286 is open and explicitly names missing support for common accounting
  forms like `1,234`, `(123)`, `$1.2m`, and unit-qualified values.
- Backend `multipass_extraction.py` currently accepts pass3a metric values via
  `float(val)`, which skips currency/unit-qualified strings and therefore drops
  otherwise source-bound metric values.
- Script-side parsers already cover some formats, but the production backend
  pass3a path needs the same deterministic behavior.

## Hard Stops

- Do not run count-24, count-32, broad extraction, random samples, backfills,
  service routes, or runtime jobs.
- Do not mutate DB, Qdrant, Redis, news, memory, source PDFs, prompts, gold
  labels, schema, model/runtime/GPU/service config, or production data.
- Do not widen metric ontology or relax validation gates.
- Do not implement the full #286 provenance schema in this slice.

## Required Implementation

- Add a focused RED regression first for pass3a accounting-number strings.
- Implement the smallest backend extraction change in `multipass_extraction.py`.
- Preserve existing table/document scale behavior when values have no explicit
  unit suffix.
- Avoid double-scaling when the value itself carries an explicit suffix such as
  `m`, `million`, `bn`, or `billion`.
- Preserve fail-closed behavior for nonnumeric strings.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_accounting_number_parse_v1_20260616.md`
- Focused RED test before implementation.
- Focused GREEN test after implementation.
- `python3 -m py_compile financial-engine_v2/backend/app/services/multipass_extraction.py`
- Targeted `ruff check` on touched Python files.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_accounting_number_parse_v1_20260616.md --repo-root .`
