# Nightly News Cron Restore - 2026-06-07

Status: DONE_WITH_RISK

## Scope

Restored the repository-side cron target used by the installed crontab:

```text
/home/l4nd0/tenn/financial-engine_v2/scripts/nightly_news.sh
```

The implementation was made in the clean sibling worktree:

```text
/home/l4nd0/tenn-nightly-news-cron-restore-v1-20260607
```

## Current Evidence

- Live crontab points at `/home/l4nd0/tenn/financial-engine_v2/scripts/nightly_news.sh`.
- That target was missing in the dirty shared live checkout before this patch was applied.
- The validated patch has now been copied into the dirty shared live checkout without touching unrelated dirty files.
- Current `origin/main` also lacked `financial-engine_v2/scripts/nightly_news.sh`.
- Current `origin/main` news pipeline uses `scripts/fetch_daily_news.py` and `scripts/build_news_chunks.py`.
- Current `origin/main` lacked the default ticker universe required by `scripts/fetch_daily_news.py`.
- Older `nightly_news.sh` wrappers call missing current files such as `scripts/load_news_to_qdrant.py`, so they were not copied verbatim.

## Files Changed

- `.gitignore`
- `docs/agent_tasks/nightly_news_cron_restore_v1_20260607.md`
- `financial-engine_v2/data/raw/asx_ticker_universe.txt`
- `financial-engine_v2/scripts/nightly_news.sh`
- `scripts/fetch_daily_news.py`
- `scripts/news_pipeline/cli_common.py`
- `scripts/news_pipeline/providers/__init__.py`
- `scripts/news_pipeline/providers/newspaper4k.py`
- `scripts/test_news_pipeline_providers.py`
- `scripts/test_nightly_news_wrapper.py`
- `reports/agent_jobs/nightly_news_cron_restore_v1_20260607/README.md`

## Behavior

- The wrapper defaults to provider `newspaper4k`, with overrides through `NIGHTLY_NEWS_PROVIDERS` or `NEWS_PROVIDERS`.
- The default newspaper4k profile is the bounded daily RSS-only path:
  `--newspaper4k-source-profile daily`, max 15 articles per source, max 60
  total articles, 10 second request timeout, and no Playwright.
- It runs `scripts/fetch_daily_news.py`, then `scripts/build_news_chunks.py --embed-backend hash`.
- It writes log, status, fetch, chunk, and health JSON artifacts under `NIGHTLY_NEWS_LOG_DIR`.
- It fails by default when fetched articles, written chunks, or provider errors miss the configured health thresholds.
- It supports `NIGHTLY_NEWS_DRY_RUN=1` without touching live news DBs.
- It keeps EODHD keys environment-only and does not pass them in process argv.
- Provider progress is written to stderr so fetch/chunk JSON artifacts remain parseable.
- Health parsing tolerates a prefixed log line and still writes a health artifact instead of crashing before the health file exists.

## Validation

Passed:

```text
python3 /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/scripts/agent_job_contract.py validate docs/agent_tasks/nightly_news_cron_restore_v1_20260607.md
bash -n financial-engine_v2/scripts/nightly_news.sh
python3 -m unittest scripts.test_nightly_news_wrapper
python3 -m unittest scripts.test_news_pipeline_providers
python3 -m unittest scripts.test_news_pipeline_workflows
python3 scripts/fetch_daily_news.py --dry-run --tickers BHP --news-articles-db /tmp/tenn-news-dryrun.sqlite --news-runs-root /tmp/tenn-news-runs
git diff --check
python3 /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/scripts/agent_job_contract.py check-diff docs/agent_tasks/nightly_news_cron_restore_v1_20260607.md --repo-root /home/l4nd0/tenn-nightly-news-cron-restore-v1-20260607 --no-write-report
NIGHTLY_NEWS_DRY_RUN=1 NIGHTLY_NEWS_LOG_DIR=/tmp/tmp.1Th5V1zqCi/logs TENN_NEWS_ARTIFACT_ROOT=/tmp/tmp.1Th5V1zqCi/qual_context /home/l4nd0/tenn/financial-engine_v2/scripts/nightly_news.sh
NIGHTLY_NEWS_SINCE_HOURS=168 NIGHTLY_NEWS_NEWSPAPER4K_MAX_ARTICLES_PER_SOURCE=2 NIGHTLY_NEWS_NEWSPAPER4K_MAX_TOTAL_ARTICLES=3 NIGHTLY_NEWS_NEWSPAPER4K_SLEEP_SECONDS=0 NIGHTLY_NEWS_LOG_DIR=/tmp/tmp.zUetWp6GIj/logs TENN_NEWS_ARTIFACT_ROOT=/tmp/tmp.zUetWp6GIj/qual_context /home/l4nd0/tenn/financial-engine_v2/scripts/nightly_news.sh
python3 -m json.tool /tmp/tmp.zUetWp6GIj/logs/nightly_news_2026-06-07_173942.fetch.json
python3 -m json.tool /tmp/tmp.zUetWp6GIj/logs/nightly_news_2026-06-07_173942.health.json
python3 -m json.tool /tmp/tmp.zUetWp6GIj/logs/nightly_news_2026-06-07_173942.status.json
```

Wrapper test coverage:

- Dry-run writes status and health JSON without creating temp news DBs.
- Default dry-run uses `newspaper4k`.
- Capture-backed EODHD run fetches articles, builds temp SQLite context chunks, and passes health.
- Zero-fetch/provider-error run exits nonzero and writes failing health JSON.

Provider test coverage:

- `newspaper4k` defaults to the bounded daily profile.
- Explicit broad profile override remains available.
- The provider does not pass unsupported `playwright_domains` to the current collector.
- The provider writes progress to stderr, not stdout.
- `fetch_daily_news.py --dry-run` reports bounded newspaper4k provider options without writes.

## Not Done

- Did not edit installed crontab.
- Did not push, open PRs, comment on issues, or mutate GitHub.
- Did not run live provider ingestion against production news stores.
- Did not edit memory directly; added an ad hoc future-session memory note under `/home/l4nd0/.codex/memories/extensions/ad_hoc/notes/`.
- Did not mutate Qdrant, Redis, production DBs, runtime services, memory stores, source PDFs, gold labels, extraction prompts, parser routing, model/GPU config, migrations, or backfills.

## Live Dry-Run Result

Passed through the installed cron path:

```text
/home/l4nd0/tenn/financial-engine_v2/scripts/nightly_news.sh
```

Result:

- exit code: 0
- resolved root: `/home/l4nd0/tenn`
- ticker count: 375
- provider default: `newspaper4k`
- fetch Python: `/home/l4nd0/tenn/integrations/newspaper4k_au/.venv/bin/python`
- dry-run status: success
- fetch/build phases: skipped by `NIGHTLY_NEWS_DRY_RUN=1`
- status JSON: `/tmp/tmp.1Th5V1zqCi/logs/nightly_news_2026-06-07_173933.status.json`
- health JSON: `/tmp/tmp.1Th5V1zqCi/logs/nightly_news_2026-06-07_173933.health.json`

## Live Bounded Smoke Result

Passed through the installed cron path with temporary news stores:

```text
NIGHTLY_NEWS_SINCE_HOURS=168
NIGHTLY_NEWS_NEWSPAPER4K_MAX_ARTICLES_PER_SOURCE=2
NIGHTLY_NEWS_NEWSPAPER4K_MAX_TOTAL_ARTICLES=3
NIGHTLY_NEWS_NEWSPAPER4K_SLEEP_SECONDS=0
NIGHTLY_NEWS_LOG_DIR=/tmp/tmp.zUetWp6GIj/logs
TENN_NEWS_ARTIFACT_ROOT=/tmp/tmp.zUetWp6GIj/qual_context
/home/l4nd0/tenn/financial-engine_v2/scripts/nightly_news.sh
```

Result:

- exit code: 0
- provider default: `newspaper4k`
- source profile: `daily`
- fetch Python: `/home/l4nd0/tenn/integrations/newspaper4k_au/.venv/bin/python`
- fetched: 1
- inserted: 1
- chunks written: 2
- health status: success
- problems: none
- status JSON: `/tmp/tmp.zUetWp6GIj/logs/nightly_news_2026-06-07_173942.status.json`
- fetch JSON: `/tmp/tmp.zUetWp6GIj/logs/nightly_news_2026-06-07_173942.fetch.json`
- health JSON: `/tmp/tmp.zUetWp6GIj/logs/nightly_news_2026-06-07_173942.health.json`

Remaining risk: a real scheduled run still depends on its scheduled time, current network/provider behavior, and the production news artifact root. Production news stores were intentionally not exercised here.
