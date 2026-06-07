---
job_id: nightly_news_cron_restore_v1_20260607
lane: Evaluation
supporting_lanes:
  - Reporting
  - Repo Hygiene
owner: Codex
allowed_files:
  - .gitignore
  - docs/agent_tasks/nightly_news_cron_restore_v1_20260607.md
  - financial-engine_v2/scripts/nightly_news.sh
  - financial-engine_v2/data/raw/asx_ticker_universe.txt
  - scripts/fetch_daily_news.py
  - scripts/news_pipeline/cli_common.py
  - scripts/news_pipeline/providers/__init__.py
  - scripts/news_pipeline/providers/newspaper4k.py
  - scripts/test_news_pipeline_providers.py
  - scripts/test_nightly_news_wrapper.py
  - reports/agent_jobs/nightly_news_cron_restore_v1_20260607/README.md
approval_required: true
timeout_seconds: 1800
output_dir: reports/agent_jobs/nightly_news_cron_restore_v1_20260607
mutation_mode: safe_extension
production_data_access: false
---

# Task

Restore the installed nightly-news cron target on current `origin/main` without
reintroducing the older missing Qdrant/newspaper4k wrapper path.

# Background

Live crontab currently calls:

```text
0 2 * * * /home/l4nd0/tenn/financial-engine_v2/scripts/nightly_news.sh
```

The file is missing from the live `/home/l4nd0/tenn` path. Current `origin/main`
also lacks the default ASX ticker universe required by the current
`scripts/fetch_daily_news.py` pipeline.

# Required Behavior

- Add `financial-engine_v2/scripts/nightly_news.sh`.
- Restore the bounded newspaper4k daily provider/profile path and use the current
  news pipeline entrypoints:
  - `scripts/fetch_daily_news.py`
  - `scripts/build_news_chunks.py`
- Default to `newspaper4k` unless overridden by
  `NIGHTLY_NEWS_PROVIDERS`.
- Use `--newspaper4k-source-profile daily`, capped article counts, short request
  timeout, and no Playwright by default.
- Require a non-empty ticker universe before fetching.
- Build the SQLite news context fallback after fetch.
- Emit log, status JSON, fetch JSON, chunk JSON, and health JSON artifacts under
  the nightly log directory.
- Fail by default when fetched article count is below `NIGHTLY_NEWS_MIN_FETCHED`
  so a zero-article run is not reported as healthy.
- Support temp-path validation without mutating live news stores.

# Hard Boundaries

- Do not edit crontab, systemd timers, local runner config, symlinks, or host
  runtime config.
- Do not push.
- Do not create, edit, close, label, reopen, or comment on GitHub issues or PRs.
- Do not run live news ingestion against production DBs during validation.
- Do not mutate Qdrant, Redis, production DBs, memory stores, source PDFs, gold
  labels, extraction prompts, parser routing, model/GPU config, backfills, or
  migrations.
- Do not restore the older `load_news_to_qdrant.py`/Qdrant cron wrapper in this
  task.

# Required Validation

- Validate this task card with available Tenn task-card tooling.
- Run focused wrapper tests that use temp DBs and provider capture fixtures.
- Run `git diff --check`.
- Run task-card `check-diff` with `--no-write-report`.

# Definition Of Done

- Cron target exists in the repo at the path used by live crontab.
- Default ASX ticker universe exists at the path used by current news pipeline
  defaults.
- Focused validation passes without touching live news stores.
- Remaining live deployment state is reported separately because this task does
  not edit installed crontab or copy files into the dirty shared checkout.
