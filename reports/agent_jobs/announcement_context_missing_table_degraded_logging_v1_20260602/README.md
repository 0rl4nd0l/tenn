# Announcement Context Missing Table Degraded Logging

Issue: #84

Branch: `safe/announcement-context-missing-table-degraded-v1-20260602`

Worktree: `/home/l4nd0/tenn-announcement-context-missing-table-degraded-v1-20260602`

## Summary

This safe-extension slice keeps `cockpit_announcement_context` schema absence visible as degraded context, but stops warning-logging the known optional missing-table query when the backend falls back to `documents_pdf_excerpt`.

The backend response still reports:

- `announcement_context_fallback_used=true`
- an `errors[]` entry naming the unavailable materialized announcement context and the document-excerpt fallback
- fallback rows with `context_source="documents_pdf_excerpt"` when eligible documents exist

Non-optional query failures still log `WARNING` and remain blocking errors.

## Changed Files

- `financial-engine_v2/backend/app/api/context.py`
- `financial-engine_v2/backend/tests/test_context_endpoints.py`
- `docs/agent_tasks/announcement_context_missing_table_degraded_logging_v1_20260602.md`
- `reports/agent_jobs/announcement_context_missing_table_degraded_logging_v1_20260602/*`

## Boundaries

No schema migration, table creation, table population, materializer execution, DB/Qdrant/news/memory write, source-label relaxation, financial-truth mutation, parser routing, extraction prompt, gold-label, runtime, model, GPU, Docker, or service-config change was made.

## Relationship To PR #180

PR #180 remains the report-only #84 schema ownership audit. This branch is a separate narrow implementation follow-up that changes only degraded logging behavior and focused tests. It does not claim the schema ownership question is fully resolved.

## Closeout Decision

`PARTIAL_FIX_KEEP_OPEN`.

Issue #84 should stay open until the report-only schema audit and any later schema/materializer ownership decision are accepted or superseded.
