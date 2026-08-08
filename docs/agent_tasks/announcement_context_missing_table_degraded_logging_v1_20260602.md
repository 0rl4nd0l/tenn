---
job_id: announcement_context_missing_table_degraded_logging_v1_20260602
lane: Provenance
supporting_lanes:
  - Query Orchestration
  - Reporting
  - Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/announcement_context_missing_table_degraded_logging_v1_20260602.md
  - reports/agent_jobs/announcement_context_missing_table_degraded_logging_v1_20260602/README.md
  - reports/agent_jobs/announcement_context_missing_table_degraded_logging_v1_20260602/status.json
  - reports/agent_jobs/announcement_context_missing_table_degraded_logging_v1_20260602/validation.json
  - reports/agent_jobs/announcement_context_missing_table_degraded_logging_v1_20260602/diff-check.json
  - financial-engine_v2/backend/app/api/context.py
  - financial-engine_v2/backend/tests/test_context_endpoints.py
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/announcement_context_missing_table_degraded_logging_v1_20260602
mutation_mode: safe_extension
production_data_access: false
github_comment_targets:
  - 84
---

# Announcement Context Missing Table Degraded Logging

Issue: #84

## Objective

Implement a narrow follow-up to the report-only #84 schema audit: keep missing
`cockpit_announcement_context` behavior explicitly degraded and source-honest,
but stop emitting noisy backend warning logs for the known optional missing-table
case when `documents_pdf_excerpt` fallback is used.

## Scope

Primary lane: Provenance.

Target layer: backend Retrieval/Analysis context serving.

Allowed behavior:

- Preserve `announcement_context_fallback_used=true` when the materialized table
  is missing.
- Preserve `errors[]` evidence that the materialized context table is missing.
- Preserve `documents_pdf_excerpt` fallback behavior and source identity.
- Keep non-missing-table query failures as warnings/errors.
- Add focused regression coverage proving the optional missing-table path is not
  warning-logged while unrelated query failures still are.

## Hard Boundaries

- No DB, Postgres, Qdrant, SQLite, news, memory, or financial-truth writes.
- No schema migration, table creation, or materializer execution.
- No source-label relaxation.
- No parser routing, extraction prompt, gold-label, runtime, model, GPU, Docker,
  or service-config changes.
- No broad context API redesign.
- No production data access.
- No unrelated dirty work.

## Required Preflight

1. Validate this task card.
2. Run registry `list-active` and `check-overlap`.
3. Claim the task only if no HIGH overlap exists.
4. Confirm the only overlapping open PR for issue #84 is report-only PR #180 and
   it does not touch the implementation files.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/announcement_context_missing_table_degraded_logging_v1_20260602.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/announcement_context_missing_table_degraded_logging_v1_20260602.md`
- focused backend context endpoint tests
- targeted Ruff for changed Python files
- JSON validation for report artifacts
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/announcement_context_missing_table_degraded_logging_v1_20260602.md`

## Closeout Policy

Use `refs #84` unless the issue owner accepts this narrow degraded-logging slice
as the final product remediation. Keep #84 open while PR #180 and any schema
ownership decision remain unmerged or unresolved.
