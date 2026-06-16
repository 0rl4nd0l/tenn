---
job_id: extraction_payload_field_provenance_v1_20260616
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_payload_field_provenance_v1_20260616.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - reports/agent_jobs/extraction_payload_field_provenance_v1_20260616/README.md
  - reports/agent_jobs/extraction_payload_field_provenance_v1_20260616/status.json
  - reports/agent_jobs/extraction_payload_field_provenance_v1_20260616/validation.json
  - reports/agent_jobs/extraction_payload_field_provenance_v1_20260616/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_payload_field_provenance_v1_20260616
mutation_mode: safe_extension
allow_audit_code_changes: true
production_data_access: false
github_mutation_allowed: true
---

# Extraction Payload Field Provenance

## Objective

Implement one bounded #286 extraction-only safe extension: add structured
payload-level field provenance for pass4-reconciled metrics.

## Current Evidence

- Issue #286 is open, ready, P1, and asks for field-level provenance including
  page, excerpt, unit, currency, scale, table label, or extraction run id.
- PR #349 merged the accounting-number parsing child of #286; this slice must
  not revisit numeric coercion except as a guardrail.
- `multipass_extraction.py` already emits string `provenance`, `row_refs`,
  `metric_source_scales`, and `metric_scale_sources`, but downstream consumers
  do not get one structured per-metric object tying source/page/row/scale/currency
  together in the payload.

## Hard Stops

- Do not run count-24, count-32, broad extraction, random samples, backfills,
  service routes, or runtime jobs.
- Do not mutate DB, Qdrant, Redis, news, memory, source PDFs, prompts, gold
  labels, schema, model/runtime/GPU/service config, or production data.
- Do not widen metric ontology or relax validation gates.
- Do not implement persistence/schema migration in this slice.
- Do not reopen LBL companion period binding unless a focused guardrail fails.

## Required Implementation

- Add a focused RED regression first for a `field_provenance` map in the pass4
  payload.
- Implement the smallest backend extraction change in `multipass_extraction.py`.
- Preserve existing `provenance`, `row_refs`, `metric_source_scales`, and
  `metric_scale_sources` behavior.
- Include only source-bound fields already available in the extraction payload:
  metric, source table, page number/tag, row reference/excerpt, scale,
  scale source, currency, period type, and period end.
- Leave unavailable fields absent or `unknown`; do not invent source document or
  run identifiers.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_payload_field_provenance_v1_20260616.md`
- Focused RED test before implementation.
- Focused GREEN test after implementation.
- `python3 -m py_compile financial-engine_v2/backend/app/services/multipass_extraction.py`
- Targeted `ruff check` on touched Python files.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_payload_field_provenance_v1_20260616.md --repo-root .`
