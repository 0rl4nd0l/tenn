---
job_id: a2m_news_projection_path_remediation_v1_20260525
lane: Query Orchestration
supporting_lanes:
  - Provenance
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/a2m_news_projection_path_remediation_v1_20260525.md
  - reports/agent_jobs/a2m_news_projection_path_remediation_v1_20260525/README.md
  - reports/agent_jobs/a2m_news_projection_path_remediation_v1_20260525/status.json
  - reports/agent_jobs/a2m_news_projection_path_remediation_v1_20260525/news_projection_path_map.json
  - reports/agent_jobs/a2m_news_projection_path_remediation_v1_20260525/a2m_evidence_route_matrix.json
  - reports/agent_jobs/a2m_news_projection_path_remediation_v1_20260525/projection_gap_register.json
  - reports/agent_jobs/a2m_news_projection_path_remediation_v1_20260525/recommended_child_task_card.md
  - reports/agent_jobs/a2m_news_projection_path_remediation_v1_20260525/validation.json
  - reports/agent_jobs/a2m_news_projection_path_remediation_v1_20260525/diff-check.json
approval_required: false
allow_audit_code_changes: true
timeout_seconds: 10800
output_dir: reports/agent_jobs/a2m_news_projection_path_remediation_v1_20260525
mutation_mode: audit_only
production_data_access: false
---

# A2M News Projection Path Remediation Audit

Audit why A2M news evidence is present in Qdrant/retrieval but SQLite or
projection paths remain `DATA_MISSING`, then identify the smallest safe
remediation path.

Execution mode is audit-only. Do not edit production code or mutate any DB,
Qdrant collection, news store, Tenn memory, company memory, market memory,
thesis memory, environment file, service process, Docker/systemd/cron
configuration, or Cockpit implementation.

Allowed writes are limited to this task card and the listed report artifacts.
All inspection must be read-only. Do not run ingestion, backfill, reindex,
resync, projection rebuild, news refresh, Qdrant loader jobs, or source-label,
alias, parser, extraction, or metric-scoring changes.

Core questions:

- Which current repo code paths write A2M/news article data into Qdrant?
- Which current repo code paths write or project article data into SQLite/news
  projection stores?
- Which SQLite files are expected by Cockpit/query routes today?
- Which SQLite files actually exist in canonical runtime/repo paths?
- Does Qdrant contain A2M evidence from a current pipeline or obsolete source?
- Is there a route/config/path mismatch between Qdrant, SQLite, projection DBs,
  reports, and Cockpit?
- What is the smallest safe next remediation, and what validation would prove
  A2M projection parity without a blind reindex or resync?

Required outputs:

- `reports/agent_jobs/a2m_news_projection_path_remediation_v1_20260525/README.md`
- `reports/agent_jobs/a2m_news_projection_path_remediation_v1_20260525/status.json`
- `reports/agent_jobs/a2m_news_projection_path_remediation_v1_20260525/news_projection_path_map.json`
- `reports/agent_jobs/a2m_news_projection_path_remediation_v1_20260525/a2m_evidence_route_matrix.json`
- `reports/agent_jobs/a2m_news_projection_path_remediation_v1_20260525/projection_gap_register.json`
- `reports/agent_jobs/a2m_news_projection_path_remediation_v1_20260525/recommended_child_task_card.md`
- `reports/agent_jobs/a2m_news_projection_path_remediation_v1_20260525/validation.json`
- `reports/agent_jobs/a2m_news_projection_path_remediation_v1_20260525/diff-check.json`

Validation:

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/a2m_news_projection_path_remediation_v1_20260525.md --write-report`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/a2m_news_projection_path_remediation_v1_20260525.md`
- JSON validation for generated JSON artifacts
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/a2m_news_projection_path_remediation_v1_20260525.md`
- final `git status --short --untracked-files=all`
- final `python3 scripts/agent_job_registry.py list-active`
