# News Pipeline Newspaper4k Replay V1

## Status

READY_FOR_LOCAL_COMMIT

## Summary

Prepared a narrow replay on a clean branch from current
`origin/migration/clean-runtime-baseline-reconstruct-v1`.

The original preserved `NEWS_PIPELINE_PR_CANDIDATE` patch did not apply cleanly
because current migration already includes a newer newspaper4k/nightly-news
implementation. The branch keeps only the still-useful compatibility and
diagnostic behavior:

- Newspaper4k provider diagnostics go to stderr.
- `playwright_domains` is passed only when the collector signature supports it.
- Focused tests cover both behaviors.

## Files

- `docs/agent_tasks/news_pipeline_newspaper4k_replay_v1_20260608.md`
- `scripts/news_pipeline/providers/newspaper4k.py`
- `scripts/test_news_pipeline_providers.py`
- `reports/agent_jobs/news_pipeline_newspaper4k_replay_v1_20260608/README.md`
- `reports/agent_jobs/news_pipeline_newspaper4k_replay_v1_20260608/status.json`
- `reports/agent_jobs/news_pipeline_newspaper4k_replay_v1_20260608/validation.json`
- `reports/agent_jobs/news_pipeline_newspaper4k_replay_v1_20260608/diff-check.json`

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/news_pipeline_newspaper4k_replay_v1_20260608.md`
  - PASS
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
  - PASS
  - `read_only=true`, `lock_acquired=false`, `active_jobs=[]`
- `python3 -m py_compile scripts/news_pipeline/providers/newspaper4k.py scripts/test_news_pipeline_providers.py`
  - PASS
- `python3 scripts/test_news_pipeline_providers.py`
  - PASS, 25 tests
- `python3 scripts/test_run_news_pipeline.py`
  - PASS, 3 tests
- `python3 scripts/fetch_daily_news.py --dry-run --providers newspaper4k --tickers BHP --news-articles-db /tmp/tenn-news-pipeline-replay-smoke/news_articles.sqlite --news-runs-root /tmp/tenn-news-pipeline-replay-smoke/news_runs`
  - PASS
  - Dry-run providers: `["newspaper4k"]`
  - Dry-run ticker sample: `["BHP"]`
- `git diff --check`
  - PASS

Final task-card `check-diff` is recorded in `diff-check.json`.

## Commit Readiness

Ready for one local commit on
`safe/news-pipeline-newspaper4k-replay-v1-20260608` if final `check-diff`
passes. Stop before push or PR.

## Unsafe Actions Avoided

- No original dirty checkout cleanup.
- No whole-file stale transplant.
- No runtime, DB, Qdrant, Redis, extraction, memory, source-PDF, gold-label,
  prompt, model/GPU, service, or production-data mutation.
- No push, PR, merge, rebase, stash, branch deletion, worktree removal, or
  GitHub mutation.
