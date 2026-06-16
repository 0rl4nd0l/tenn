---
job_id: extraction_issue286_persisted_field_provenance_v1_20260617
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_issue286_persisted_field_provenance_v1_20260617.md
  - financial-engine_v2/backend/app/models/asx_financials.py
  - financial-engine_v2/backend/app/services/pipeline.py
  - financial-engine_v2/backend/app/alembic/versions/0009_periodic_financial_metric_provenance.py
  - financial-engine_v2/backend/tests/test_db_integrity.py
  - reports/agent_jobs/extraction_issue286_persisted_field_provenance_v1_20260617/STATE.md
  - reports/agent_jobs/extraction_issue286_persisted_field_provenance_v1_20260617/DECISIONS.md
  - reports/agent_jobs/extraction_issue286_persisted_field_provenance_v1_20260617/NEXT_GOAL.md
  - reports/agent_jobs/extraction_issue286_persisted_field_provenance_v1_20260617/PR_REVIEW.md
  - reports/agent_jobs/extraction_issue286_persisted_field_provenance_v1_20260617/validation.json
  - reports/agent_jobs/extraction_issue286_persisted_field_provenance_v1_20260617/diff-check.json
approval_required: true
allow_unapproved_safe_extension: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_issue286_persisted_field_provenance_v1_20260617
mutation_mode: safe_extension
allow_audit_code_changes: true
production_data_access: false
github_mutation_allowed: true
---

# Issue 286 Persisted Field Provenance

## Objective

Implement the approved narrow issue #286 persistence slice: add additive
per-metric field provenance storage for ASX periodic financial rows and wire the
pipeline upsert path so provenance is persisted only for metric values actually
written.

## Current Evidence

- Review-board source packet:
  `reports/agent_jobs/extraction_issue286_persisted_field_provenance_review_board_v1_20260617/`
- Issue #286 remains open and requires persisted metrics to trace back to
  document/run/source excerpt/page when available.
- PR #349, PR #350, PR #351, and PR #354 are merged child/closeout slices, but
  the persistence/schema boundary remains.
- PR #289 contained older broad temporary-branch `metric_provenance` storage,
  but issue #286 stayed open because that work was partial and not coupled to
  deterministic per-field page/table evidence.

## Approved Implementation

- Add an additive JSON column on `ASXPeriodicFinancial` for per-metric
  provenance.
- Add an Alembic migration for the new column.
- Wire `_upsert_financial_rows` to copy structured `field_provenance` entries
  only for metrics whose coerced value is actually written.
- Preserve metric, source document id, extraction run id, page, excerpt or row
  reference, table/source label, scale, currency, and period evidence when
  present.
- Preserve existing row-level `source_document_id`, `confidence_metrics`,
  `period_start`, and `currency` behavior.

## Hard Stops

- Do not touch count-24.
- Do not run count-24, count-32, broad extraction, random samples, or backfills.
- Do not mutate live DB, Qdrant, Redis, news, memory, source PDFs, gold labels,
  prompts, runtime state, model/GPU/service config, or production data.
- Do not run Alembic upgrade against a live database.
- Do not change extraction prompts, widen metric ontology, or relax validation
  gates.
- Do not merge the PR.
- Do not clean, reset, stash, rebase, cherry-pick, force-push, delete branches,
  or remove worktrees.

## Required RED/GREEN Checks

- Focused RED test before implementation:
  `_upsert_financial_rows` should persist per-metric provenance and currently
  does not.
- Focused GREEN tests after implementation:
  - persists provenance for a metric whose value is written;
  - does not write provenance for absent/null metric values;
  - persisted provenance is keyed by metric;
  - preserves page, excerpt or row reference, scale, currency,
    `source_document_id`, and `extraction_run_id` when present;
  - existing `source_document_id` and `confidence_metrics` persistence still
    works.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_issue286_persisted_field_provenance_v1_20260617.md`
- Focused RED pytest before implementation.
- Focused GREEN pytest after implementation.
- Focused existing upsert/pipeline persistence tests.
- `python3 -m py_compile` for touched Python files.
- Targeted `ruff check` for touched Python files.
- Alembic migration import/sanity check without live DB upgrade.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_issue286_persisted_field_provenance_v1_20260617.md --repo-root .`
- Changed-path guard proving only approved issue #286 provenance files changed.
