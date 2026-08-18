---
job_id: a2m_news_projection_path_discovery_v1_20260524
lane: Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/a2m_news_projection_path_discovery_v1_20260524.md
  - reports/agent_jobs/a2m_news_projection_path_discovery_v1_20260524/README.md
  - reports/agent_jobs/a2m_news_projection_path_discovery_v1_20260524/status.json
  - reports/agent_jobs/a2m_news_projection_path_discovery_v1_20260524/path_parity_matrix.json
  - reports/agent_jobs/a2m_news_projection_path_discovery_v1_20260524/path_parity_matrix.csv
  - reports/agent_jobs/a2m_news_projection_path_discovery_v1_20260524/read_only_checks.json
  - reports/agent_jobs/a2m_news_projection_path_discovery_v1_20260524/validation.json
  - reports/agent_jobs/a2m_news_projection_path_discovery_v1_20260524/no_mutation_attestation.md
  - reports/agent_jobs/a2m_news_projection_path_discovery_v1_20260524/diff-check.json
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/a2m_news_projection_path_discovery_v1_20260524
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
---

# A2M News Projection Path Discovery

## Objective

Reduce or precisely classify `DATA_MISSING` around A2M SQLite/projection parity by discovering actual live news/projection paths or proving they are absent, disabled, moved, or obsolete.

## Required Audit

- Inspect repo config/env/scripts for news SQLite paths, projection outputs, Qdrant load paths, Cockpit-local projection paths, docker mounts, cron outputs, and runtime path indirection.
- Check live paths read-only.
- Query Qdrant only read-only and with `with_vectors=false` if reachable.
- Produce an A2M path/parity matrix.

## Forbidden

- No Qdrant writes, news SQLite writes, blind reindex/resync, cron/runtime config changes, one-off A2M alias fixes, or broad entity-linker rewrites.

## Validation

- Validate JSON/CSV report artifacts.
- Prove read-only checks and no-write boundaries.
- `git diff --check`.
- Task-card `check-diff`.
