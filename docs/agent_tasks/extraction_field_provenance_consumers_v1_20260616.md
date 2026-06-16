---
job_id: extraction_field_provenance_consumers_v1_20260616
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_field_provenance_consumers_v1_20260616.md
  - financial-engine_v2/backend/app/services/provenance.py
  - financial-engine_v2/backend/app/services/extraction_eval.py
  - financial-engine_v2/backend/app/services/extraction_review.py
  - financial-engine_v2/backend/tests/test_provenance_adapter.py
  - financial-engine_v2/backend/tests/test_extraction_eval.py
  - financial-engine_v2/backend/tests/test_extraction_review_service.py
  - reports/agent_jobs/extraction_field_provenance_consumers_v1_20260616/README.md
  - reports/agent_jobs/extraction_field_provenance_consumers_v1_20260616/status.json
  - reports/agent_jobs/extraction_field_provenance_consumers_v1_20260616/validation.json
  - reports/agent_jobs/extraction_field_provenance_consumers_v1_20260616/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_field_provenance_consumers_v1_20260616
mutation_mode: safe_extension
allow_audit_code_changes: true
production_data_access: false
github_mutation_allowed: true
---

# Extraction Field Provenance Consumers

## Objective

Implement one bounded #286 extraction-only safe extension: make existing
payload consumers prefer structured `field_provenance` from PR #350 while
preserving legacy `provenance` fallback.

## Current Evidence

- Issue #286 remains open and asks for field-level provenance such as page,
  excerpt, unit, currency, scale, table label, and extraction run id.
- PR #350 added payload-level `field_provenance`, but consumer adapters still
  primarily read legacy string `provenance`.
- `provenance.from_extraction_payload()` and extraction review/evaluation paths
  are narrow consumers that can use the structured payload without persistence
  or schema changes.

## Hard Stops

- Do not run count-24, count-32, broad extraction, random samples, backfills,
  service routes, or runtime jobs.
- Do not mutate DB, Qdrant, Redis, news, memory, source PDFs, prompts, gold
  labels, schema, model/runtime/GPU/service config, or production data.
- Do not widen metric ontology or relax validation gates.
- Do not implement persistence/schema migration in this slice.

## Required Implementation

- Add focused RED regressions first for `field_provenance` consumer behavior.
- Update the smallest consumer code paths to prefer structured
  `field_provenance` when present.
- Preserve fallback to legacy string `provenance`.
- Preserve existing `ProvenanceRecord` status semantics for table, prose, and
  derived evidence.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_field_provenance_consumers_v1_20260616.md`
- Focused RED tests before implementation.
- Focused GREEN tests after implementation.
- `python3 -m py_compile` on touched service files.
- Targeted `ruff check` on touched Python files.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_field_provenance_consumers_v1_20260616.md --repo-root .`
