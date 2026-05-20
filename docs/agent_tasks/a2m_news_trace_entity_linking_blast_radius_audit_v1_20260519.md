---
job_id: a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519
lane: Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519.md
  - reports/agent_jobs/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519/
  - reports/agent_jobs/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519/README.md
  - reports/agent_jobs/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519/a2m_trace_map.json
  - reports/agent_jobs/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519/entity_linking_path.md
  - reports/agent_jobs/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519/retrieval_path_trace.md
  - reports/agent_jobs/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519/blast_radius_candidates.json
  - reports/agent_jobs/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519/source_label_risk_matrix.json
  - reports/agent_jobs/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519/DATA_MISSING.md
  - reports/agent_jobs/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519/status.json
  - reports/agent_jobs/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519/validation_commands.json
  - reports/agent_jobs/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519/diff-check.json
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519
mutation_mode: audit_only
production_data_access: false
allow_audit_code_changes: true
---

# Task

Audit why A2M / A2 Milk recall or recent-news evidence previously existed in local news ingestion but did not surface correctly in Cockpit chat or reporting.

Determine whether the failure is isolated to A2M or indicates a broader entity-linking, retrieval, ranking, synthesis, freshness, or source-label completeness failure class.

# Hard Boundaries

Do not edit source code, ticker identity maps, source labels, route code, runtime configuration, financial truth, Qdrant, SQLite news stores, embeddings, memory stores, source registry, or Home producers.

Do not run news ingestion, Qdrant loaders, Qdrant resync, news backfill, deep research, or live chat flows that write session or flag artifacts.

Production data access is not approved. Prefer current code, existing reports, fixtures, and static local repo artifacts. If a live news DB or Qdrant query is required, report the exact read-only query path needed instead of running it.

# Required Preflight

Run and report:

- `pwd`
- `readlink -f /home/l4nd0/tenn-runtime`
- `git branch --show-current`
- `git rev-parse --short=12 HEAD`
- `git status --short`
- `git worktree list`
- `git show --stat --oneline --no-renames HEAD`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519.md`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519.md`

Claim only if safe. If Memory live-inventory is active, confirm this task does not touch memory stores or cleanup paths.

# Inspect

Read-only targets:

- `financial-engine_v2/backend/app/services/`
- `financial-engine_v2/backend/app/routes/`
- `financial-engine_v2/backend/tests/`
- `financial-engine_v2/config/ticker_identity_map.json`
- `financial-engine_v2/data/`
- `scripts/`
- `docs/`
- `reports/agent_jobs/*news*`
- `reports/agent_jobs/*a2m*`
- `reports/agent_jobs/*entity*`
- `reports/agent_jobs/*qdrant*`
- `reports/agent_jobs/*recall*`
- `reports/agent_jobs/*source_label*`
- `reports/agent_jobs/*query*`
- `reports/agent_jobs/*rag*`

Search terms include A2M, A2 Milk, recall, entity linking, ticker identity, aliases, news SQLite, Qdrant, loaders, freshness, recent news, source coverage, source labels, no-hit, context-only, and claim verification.

# Required Report

Write `reports/agent_jobs/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519/README.md` with:

- executive verdict;
- confirmed facts;
- inferred facts;
- speculative claims;
- DATA_MISSING;
- end-to-end trace map;
- A2M trace;
- blast-radius analysis;
- prevention plan;
- one smallest safe next task;
- hard stops and do-not-do items;
- validation commands run;
- final git status;
- registry release status if claimed;
- Project Memory save recommendation.

# Validation

Run and report:

- task-card validation;
- registry overlap and claim/release, if claimed;
- JSON artifact validation with `jq empty`;
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519.md`;
- final `git status --short`.
