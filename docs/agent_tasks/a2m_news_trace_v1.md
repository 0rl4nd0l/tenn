---
job_id: a2m_news_trace_v1
lane: Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/a2m_news_trace_v1.md
  - reports/agent_jobs/a2m_news_trace_v1/README.md
  - reports/agent_jobs/a2m_news_trace_v1/status.json
  - reports/agent_jobs/a2m_news_trace_v1/validation.json
  - reports/agent_jobs/a2m_news_trace_v1/diff-check.json
approval_required: false
allow_audit_code_changes: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/a2m_news_trace_v1
mutation_mode: audit_only
production_data_access: false
---

# Task

Close GitHub #38 by validating the existing A2M news trace, live read-only
trace, and retrieval parity artifact family into the issue-exact report path.

# Scope

Use current repo evidence and existing report artifacts to classify #38 as an
audit acceptance closeout. Do not claim product remediation beyond commits that
already exist in the current branch history.

# Hard Boundaries

- Do not reindex, resync, backfill, ingest, upsert, delete, or mutate news data.
- Do not query live chat paths that may write chat, feedback, memory, or report
  records.
- Do not edit retrieval/ranking/synthesis/source-label code, tests, prompts,
  Qdrant payloads, SQLite stores, production data, DB, Qdrant, memory, runtime,
  model, or service configuration.
- Mutate only this task card and listed issue-exact report artifacts.

# Required Outputs

- `reports/agent_jobs/a2m_news_trace_v1/README.md`
- Current validation status.
- References to the existing static audit, live read-only trace, projection path
  discovery, and retrieval parity integration evidence.

# Validation

Run and report task-card validate, registry list/check-overlap/claim/release,
current branch/HEAD/status evidence, artifact presence checks, JSON checks where
available, `git diff --check`, and task-card check-diff.
