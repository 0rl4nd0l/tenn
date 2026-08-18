---
job_id: a2m_news_projection_readonly_smoke_v1_20260525
lane: Query Orchestration
supporting_lanes:
  - Provenance
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/a2m_news_projection_readonly_smoke_v1_20260525.md
  - scripts/news_projection_path_health_check.py
  - scripts/test_news_projection_path_health_check.py
  - reports/agent_jobs/a2m_news_projection_readonly_smoke_v1_20260525/README.md
  - reports/agent_jobs/a2m_news_projection_readonly_smoke_v1_20260525/status.json
  - reports/agent_jobs/a2m_news_projection_readonly_smoke_v1_20260525/path_health.json
  - reports/agent_jobs/a2m_news_projection_readonly_smoke_v1_20260525/validation.json
  - reports/agent_jobs/a2m_news_projection_readonly_smoke_v1_20260525/diff-check.json
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/a2m_news_projection_readonly_smoke_v1_20260525
mutation_mode: safe_extension
production_data_access: false
---

# A2M News Projection Read-Only Smoke

Create a bounded read-only health check for news projection paths and A2M
reachability. This child must not run ingestion, backfill, reindex, resync,
projection rebuild, Qdrant load, Qdrant mutation, SQLite mutation, service
restart, cron/systemd edit, alias canonicalization, source-label change, parser
change, or Cockpit implementation change.

## Scope

- Add `scripts/news_projection_path_health_check.py`.
- Add focused tests for path classification and JSON shape only.
- The script may inspect configured/default paths, optional legacy candidate
  paths, current nightly summary/log presence, and read-only Qdrant count/scroll
  if Qdrant is already reachable.
- The script must default to read-only file stats and no network calls unless
  `--include-qdrant-readonly` is supplied.
- SQLite must be opened with read-only URI mode when inspected.
- Qdrant queries must use count/scroll only with vectors disabled for scroll.

## Required Output Shape

- canonical_article_db: exists/readable/path
- canonical_context_db: exists/readable/path
- legacy_candidate_dbs: exists/readable/path/mtime/size
- qdrant_news_chunks: reachable/counts/A2M counts/with_vectors_false
- latest_nightly: root/log/summary/status
- route_classification: qdrant_primary, sqlite_fallback_available, article_detail_available
- remediation_gate: no_mutation_performed, mutation_required_for_fix

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/a2m_news_projection_readonly_smoke_v1_20260525.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/a2m_news_projection_readonly_smoke_v1_20260525.md`
- focused unit test for JSON/path classification
- script dry run with no Qdrant network access
- script run with `--include-qdrant-readonly` only if Qdrant is already reachable
- JSON validation for report artifacts
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/a2m_news_projection_readonly_smoke_v1_20260525.md`

## Explicit Non-Goals

- No data repair.
- No DB copy.
- No symlink or alias workaround.
- No Qdrant write.
- No projection rebuild.
- No ingestion or provider changes.
- No Cockpit route behavior change.
