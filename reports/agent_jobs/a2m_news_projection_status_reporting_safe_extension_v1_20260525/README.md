# A2M News Projection Status Reporting Safe Extension

Generated: 2026-05-25T14:03:15+10:00

## Result

Completed as a report/status artifact extension only. No backend, Cockpit, route,
test, parser, extraction, Qdrant, SQLite, Docker, runtime, env, model, GPU, or
UI implementation files were changed.

The status surface for A2M should not say simply "A2M missing". The integrated
read-only smoke proves a split state:

- `qdrant_retrieval: ok`
- `canonical_sqlite_projection: missing`
- `legacy_sqlite_projection: evidence_present_not_current_consumer`
- `cockpit_query_route: ok_via_rag_query`
- `cockpit_status_routes: missing_404`
- `chat_synthesis: DATA_MISSING`
- `projection_repair: not_run`

## Confirmed

- Canonical integration added the parked A2M audit commit `a94acba7` and the
  parked smoke/controller commit `226dfc4a` to
  `migration/clean-runtime-baseline-reconstruct-v1`.
- Integrated smoke artifact
  `reports/agent_jobs/a2m_news_projection_readonly_smoke_v1_20260525/a2m_readonly_smoke_matrix.json`
  records Qdrant-backed A2M retrieval as user-visible through backend and
  Cockpit `/rag/query`.
- Integrated smoke artifacts record canonical NVMe SQLite projection files as
  absent.
- Legacy `/mnt/sdb2` SQLite evidence is provenance only and is not a current
  canonical route consumer.
- Live chat synthesis was not smoked because chat/session paths may write state.

## Inferred

- The user-facing defect is status clarity, not proof that every A2M data source
  is absent.
- A future Cockpit/backend status endpoint can consume this contract without
  changing retrieval flow: report Qdrant retrieval health separately from local
  SQLite projection health and legacy provenance.

## Speculative

- Projection repair may require a later approved rebuild, backfill, or data
  source decision. This task did not approve or run any repair.

## DATA_MISSING

- Fresh current live route health after 2026-05-25T13:45:28+10:00 was not
  re-smoked in this child because `production_data_access=false` and report-only
  scope were preserved.
- A canonical SQLite projection source path remains unapproved.
- Chat synthesis behavior for A2M remains unproven.

## Validation

- Child task card validation: pass.
- Registry `list-active`: one active Reporting hygiene job observed on
  unrelated files.
- Child `check-overlap`: blocked only by the two known foreign task cards being
  dirty outside the child allowlist; no active job owns child report paths.
- JSON validation: pass.
- `git diff --check`: pass.
- Task-card `check-diff`: expected warning/failure due external dirty foreign
  task cards, not due child source-file drift.

## Changed Files

- `docs/agent_tasks/a2m_news_projection_status_reporting_safe_extension_v1_20260525.md`
- `reports/agent_jobs/a2m_news_projection_status_reporting_safe_extension_v1_20260525/README.md`
- `reports/agent_jobs/a2m_news_projection_status_reporting_safe_extension_v1_20260525/status.json`
- `reports/agent_jobs/a2m_news_projection_status_reporting_safe_extension_v1_20260525/status_reporting_gap_register.json`
- `reports/agent_jobs/a2m_news_projection_status_reporting_safe_extension_v1_20260525/validation.json`
- `reports/agent_jobs/a2m_news_projection_status_reporting_safe_extension_v1_20260525/diff-check.json`
