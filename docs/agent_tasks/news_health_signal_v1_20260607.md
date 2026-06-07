---
job_id: news_health_signal_v1_20260607
lane: Evaluation
supporting_lanes:
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/news_health_signal_v1_20260607.md
  - financial-engine_v2/scripts/nightly_news.sh
  - scripts/test_nightly_news_wrapper.py
  - reports/agent_jobs/news_health_signal_v1_20260607/README.md
approval_required: true
timeout_seconds: 1800
output_dir: reports/agent_jobs/news_health_signal_v1_20260607
mutation_mode: safe_extension
production_data_access: false
---

# Task

Harden the nightly news health signal so provider/fallback no-op runs cannot
report success from stale SQLite context state.

# Background

The merged nightly cron wrapper now restores the installed cron target and
fails health when fetched articles or chunks written are zero. The remaining
P0 is success masking: a run can still look healthy when provider work did not
upsert anything new and the SQLite fallback/context DB is merely old state.

# Required Behavior

- Keep the default nightly provider path as bounded `newspaper4k` daily RSS-only.
- Add explicit health thresholds for inserted/upserted provider rows.
- Detect when the context SQLite fallback was not updated during the current
  wrapper run.
- Emit machine-readable health fields that distinguish:
  - provider fetched count,
  - provider inserted/upserted count,
  - chunk build count,
  - context DB freshness/change evidence.
- Fail health by default when:
  - fetched count is below the configured minimum,
  - inserted/upserted count is below the configured minimum,
  - chunks written are below the configured minimum,
  - provider errors exceed the configured maximum,
  - context SQLite fallback did not update for the current run.
- Preserve temp-path validation without mutating production news stores.

# Hard Boundaries

- Do not edit crontab, systemd timers, runner config, symlinks, or host runtime
  config.
- Do not push, merge, or mutate GitHub in this task.
- Do not run live news ingestion against production DBs during validation.
- Do not mutate Qdrant, Redis, production DBs, memory stores, source PDFs, gold
  labels, extraction prompts, parser routing, model/GPU config, backfills, or
  migrations.
- Do not change provider source defaults away from bounded `newspaper4k` daily.

# Required Validation

- Validate this task card with available Tenn task-card tooling.
- Run focused wrapper tests with temp DBs and provider capture fixtures.
- Run a temp-artifact wrapper validation that proves stale/no-op fallback state
  fails health.
- Run `git diff --check`.
- Run task-card `check-diff` with `--no-write-report`.

# Definition Of Done

- Nightly health fails a zero-upsert/stale-fallback run by default.
- Nightly health still passes a capture-backed temp run that fetches, inserts,
  builds chunks, and updates the context DB in the current run.
- Health JSON includes enough evidence to explain the pass/fail decision.
- Production news stores and host scheduler state are untouched.
