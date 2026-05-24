---
job_id: a2m_news_live_trace_readonly_v1_20260524
lane: Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/a2m_news_live_trace_readonly_v1_20260524.md
  - reports/agent_jobs/a2m_news_live_trace_readonly_v1_20260524/README.md
  - reports/agent_jobs/a2m_news_live_trace_readonly_v1_20260524/status.json
  - reports/agent_jobs/a2m_news_live_trace_readonly_v1_20260524/trace_artifacts.json
  - reports/agent_jobs/a2m_news_live_trace_readonly_v1_20260524/sqlite_inventory.json
  - reports/agent_jobs/a2m_news_live_trace_readonly_v1_20260524/qdrant_probe.json
  - reports/agent_jobs/a2m_news_live_trace_readonly_v1_20260524/retrieval_trace.json
  - reports/agent_jobs/a2m_news_live_trace_readonly_v1_20260524/no_mutation_attestation.md
  - reports/agent_jobs/a2m_news_live_trace_readonly_v1_20260524/diff-check.json
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/a2m_news_live_trace_readonly_v1_20260524
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
---

# A2M News Live Trace Read-only

## Objective

Trace current local A2M news storage, projection, Qdrant payload availability, and retrieval-path code alignment without mutating SQLite, Qdrant, news stores, or runtime topology.

## Allowed Work

- Read-only SQLite probes.
- Qdrant read-only scroll/query with `with_vectors=false`.
- Code-path inspection of ticker, `primary_ticker`, and `tickers` handling.
- Report-local trace artifacts.

## Forbidden

- No blind reindex/resync, Qdrant write, news SQLite write, broad entity-linker rewrite, alias hardcode, Docker/runtime changes, or live chat route smoke that may persist state.

## Validation

- Validate this task card.
- Prove read-only store access and `with_vectors=false` Qdrant access if Qdrant is reachable.
- Validate JSON artifacts and run `git diff --check`.
