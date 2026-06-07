---
job_id: news_context_path_alignment_v1_20260607
lane: Evaluation
supporting_lanes:
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/news_context_path_alignment_v1_20260607.md
  - financial-engine_v2/cockpit/core/config.py
  - financial-engine_v2/cockpit/integrations/qual_context_bootstrap.py
  - financial-engine_v2/scripts/test_cockpit_news_context_path.py
  - reports/agent_jobs/news_context_path_alignment_v1_20260607/README.md
approval_required: true
timeout_seconds: 1800
output_dir: reports/agent_jobs/news_context_path_alignment_v1_20260607
mutation_mode: safe_extension
production_data_access: false
---

# Task

Align Cockpit news-context DB resolution with the nightly news artifact root so
fresh cron-built SQLite context data is not masked by stale repo-local ignored
fallback files.

# Background

The merged nightly news wrapper writes `news.sqlite` to the resolved nightly
artifact root. On the current host that is the NVMe path
`/mnt/tenn-nvme2/tenn/financial-engine_v2/reports/qual_context/news.sqlite`.
Cockpit launches from `financial-engine_v2` and its default config points to
`reports/qual_context/news.sqlite`. The current resolver chooses an existing
stale repo-local ignored DB before considering the nightly artifact root.

# Required Behavior

- Preserve the documented `COCKPIT_NEWS_DB_PATH` override as highest priority.
- Allow Cockpit to use the same `TENN_NEWS_CONTEXT_DB` and
  `TENN_NEWS_ARTIFACT_ROOT` surfaces as the nightly wrapper.
- When Cockpit is using the default relative `reports/qual_context/news.sqlite`,
  prefer a fresher existing nightly artifact-root `news.sqlite` over an older
  repo-local ignored DB.
- Do not change provider defaults, ingestion behavior, or runtime scheduler
  state.
- Do not mutate production news stores in validation.

# Hard Boundaries

- Do not edit crontab, systemd timers, Docker runtime config, host env files, or
  symlinks.
- Do not push, merge, or mutate GitHub in this task.
- Do not run live news ingestion against production DBs during validation.
- Do not mutate Qdrant, Redis, production DBs, memory stores, source PDFs, gold
  labels, extraction prompts, parser routing, model/GPU config, backfills, or
  migrations.
- Preserve the dirty live checkout by working only in a clean sibling worktree.

# Required Validation

- Validate this task card with Tenn tooling when available; otherwise record
  `DATA_MISSING` for validator availability.
- Add focused unit tests for env override handling and fresher artifact-root
  selection with temp files.
- Run the focused Cockpit news-context path test.
- Run `git diff --check`.
- Run task-card `check-diff` when tooling is available and safe; otherwise
  record `DATA_MISSING`.

# Definition Of Done

- Cockpit path resolution cannot silently choose stale default repo-local news
  data when a fresher nightly artifact-root DB exists.
- Existing explicit absolute path behavior remains deterministic.
- Validation uses temporary artifacts only.
