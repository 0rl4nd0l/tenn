---
job_id: news_pipeline_newspaper4k_replay_v1_20260608
lane: Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/news_pipeline_newspaper4k_replay_v1_20260608.md
  - scripts/news_pipeline/providers/newspaper4k.py
  - scripts/test_news_pipeline_providers.py
  - reports/agent_jobs/news_pipeline_newspaper4k_replay_v1_20260608/README.md
  - reports/agent_jobs/news_pipeline_newspaper4k_replay_v1_20260608/status.json
  - reports/agent_jobs/news_pipeline_newspaper4k_replay_v1_20260608/validation.json
  - reports/agent_jobs/news_pipeline_newspaper4k_replay_v1_20260608/diff-check.json
approval_required: true
timeout_seconds: 1800
output_dir: reports/agent_jobs/news_pipeline_newspaper4k_replay_v1_20260608
mutation_mode: safe_extension
production_data_access: false
---

# News Pipeline Newspaper4k Replay V1

## Objective

Replay the still-useful portion of the preserved `NEWS_PIPELINE_PR_CANDIDATE`
onto a clean branch from current
`origin/migration/clean-runtime-baseline-reconstruct-v1`.

The preserved patch/archive from the dirty `tmp/sloppy-fix-demo` checkout did
not apply cleanly because the current migration baseline already contains a
newer newspaper4k and nightly-news implementation. This task therefore keeps the
replay narrow: preserve provider diagnostics on stderr and compatibility with
collector versions that do not accept a `playwright_domains` keyword.

## Scope

Allowed:

- Update `scripts/news_pipeline/providers/newspaper4k.py`.
- Update focused provider tests in `scripts/test_news_pipeline_providers.py`.
- Add this task card and the report artifacts under this task's output
  directory.

Forbidden:

- Do not restore, clean, or mutate the original dirty `tmp/sloppy-fix-demo`
  checkout.
- Do not transplant whole stale files from the dirty branch.
- Do not edit nightly wrapper, CLI, provider registry, dependency, Cockpit,
  runtime, DB, Qdrant, Redis, extraction, memory, source-PDF, gold-label,
  prompt, model/GPU, service, or production-data state.
- Do not push, open PR, merge, rebase, stash, delete branches, remove
  worktrees, or mutate GitHub.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/news_pipeline_newspaper4k_replay_v1_20260608.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 -m py_compile scripts/news_pipeline/providers/newspaper4k.py scripts/test_news_pipeline_providers.py`
- `python3 scripts/test_news_pipeline_providers.py`
- `python3 scripts/test_run_news_pipeline.py`
- `python3 scripts/fetch_daily_news.py --dry-run --providers newspaper4k --tickers BHP --news-articles-db /tmp/tenn-news-pipeline-replay-smoke/news_articles.sqlite --news-runs-root /tmp/tenn-news-pipeline-replay-smoke/news_runs`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/news_pipeline_newspaper4k_replay_v1_20260608.md --repo-root .`

## Stop Boundary

Commit only the allowlisted files if validation passes, then stop before push or
PR.
