---
job_id: cockpit_home_news_snapshot_v1_20260508
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_home_news_snapshot_v1_20260508.md
  - cockpit-ui/app/api/cockpit/home/route.ts
  - cockpit-ui/lib/cockpit-home-api.ts
  - cockpit-ui/types/cockpit-home.ts
  - cockpit-ui/components/cockpit/home/
  - cockpit-ui/lib/mock/cockpit-home-fixtures.ts
  - cockpit-ui/components/cockpit/home/*.test.tsx
  - cockpit-ui/lib/*.test.ts
  - reports/agent_jobs/cockpit_home_news_snapshot_v1_20260508/
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 2400
output_dir: reports/agent_jobs/cockpit_home_news_snapshot_v1_20260508
mutation_mode: safe_extension
production_data_access: false
---

# Task

Retry Cockpit Home News Snapshot / Market Movers v1 after news dirty-diff clearance.

# Mode

Audit first. Proceed to safe extension only if task-card validation passes, shared registry and file preflight are clean, and there is no active overlap or hard-stop condition.

# Boundaries

Do not touch Qdrant, news SQLite stores, embeddings, ingestion/backfill runtime, financial truth, extraction, parser/gold labels, memory, Holdings, Marketplace, Watchlist, Commentary, legacy chat/source-label integration branches, production data, or unrelated dirty files.

# Validation

Run relevant Cockpit UI type/test checks for touched files, `git diff --check`, and `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_home_news_snapshot_v1_20260508.md`.

# Report

Write `reports/agent_jobs/cockpit_home_news_snapshot_v1_20260508/README.md` with preflight evidence, implementation or blocked result, validation results, final status, DATA_MISSING, remaining risks, and save recommendation.
