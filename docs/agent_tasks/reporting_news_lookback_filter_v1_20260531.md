---
job_id: reporting_news_lookback_filter_v1_20260531
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/reporting_news_lookback_filter_v1_20260531.md
  - reports/agent_jobs/reporting_news_lookback_filter_v1_20260531/README.md
  - reports/agent_jobs/reporting_news_lookback_filter_v1_20260531/status.json
  - reports/agent_jobs/reporting_news_lookback_filter_v1_20260531/diff-check.json
  - cockpit-ui/components/cockpit/news/news-screen.tsx
  - cockpit-ui/components/cockpit/news/news-screen.test.tsx
approval_required: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/reporting_news_lookback_filter_v1_20260531
mutation_mode: safe_extension
production_data_access: false
allow_unapproved_safe_extension: true
---

# Task

Safely remediate GitHub issue #49 by wiring the Cockpit News Lookback selector to the existing `/rag/query` news date filter contract.

# Scope

This is a Cockpit UI client-only Reporting change. The backend already accepts `date_from` and `date_to` on `RagQueryRequest` and passes them through to `query_news_chunks`. Do not change backend retrieval logic, RAG ranking, storage, source labels, financial truth, memory, production data, runtime services, or GPU/LLM configuration.

# Validation

- Validate task card and claim the job before writes.
- Add focused component/unit coverage that proves Lookback is represented in the `/rag/query` request payload.
- Run focused Cockpit UI tests and lint/type checks for touched files.
- Run `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/reporting_news_lookback_filter_v1_20260531.md` before closeout.
