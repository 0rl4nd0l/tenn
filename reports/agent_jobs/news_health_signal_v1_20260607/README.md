# News Health Signal - 2026-06-07

Status: DONE_WITH_RISK

## Scope

Hardened `financial-engine_v2/scripts/nightly_news.sh` on merged `origin/main`
so nightly news health cannot report success when provider work fetches or
upserts nothing and the SQLite fallback/context DB is only stale state.

Implementation worktree:

```text
/home/l4nd0/tenn-news-health-signal-v1-20260607
```

Baseline:

```text
origin/main 8bd82c87c5cbbc94729e223eb3655053843bedbc
```

## Files Changed

- `docs/agent_tasks/news_health_signal_v1_20260607.md`
- `financial-engine_v2/scripts/nightly_news.sh`
- `scripts/test_nightly_news_wrapper.py`
- `reports/agent_jobs/news_health_signal_v1_20260607/README.md`

## Behavior

- Added `NIGHTLY_NEWS_MIN_UPSERTED` / `NEWS_MIN_UPSERTED`, default `1`.
- Added `NIGHTLY_NEWS_REQUIRE_CONTEXT_FRESH` / `NEWS_REQUIRE_CONTEXT_FRESH`,
  default enabled.
- Added `NIGHTLY_NEWS_MIN_CONTEXT_RECENT_CHUNKS` /
  `NEWS_MIN_CONTEXT_RECENT_CHUNKS`, defaulting to `NIGHTLY_NEWS_MIN_CHUNKS`.
- Health now records context SQLite fallback evidence:
  - before/after DB existence, size, mtime, chunk count, max published timestamp,
  - whether the context DB changed during this wrapper run,
  - provider-run window cutoff,
  - recent news chunk count for the current window.
- Health fails by default when:
  - fetched count is below threshold,
  - inserted/upserted count is below threshold,
  - chunks written are below threshold,
  - provider errors exceed threshold,
  - context DB/table is missing,
  - context DB did not change during the run,
  - recent context news chunks for the current provider window are below
    threshold.

## Validation

Passed:

```text
python3 /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/scripts/agent_job_contract.py validate docs/agent_tasks/news_health_signal_v1_20260607.md
bash -n financial-engine_v2/scripts/nightly_news.sh
python3 -m unittest scripts.test_nightly_news_wrapper
python3 -m unittest scripts.test_news_pipeline_providers scripts.test_news_pipeline_workflows
```

Temp-artifact duplicate/no-upsert smoke:

```text
tmpdir: /tmp/tmp.j2Rr1G3mda
first run: exit 0, health success, fetched 2, inserted 2, chunks_written 2
second run: exit 1, health failure, fetched 2, inserted 0, deduped 2, chunks_written 2
second problem: inserted/upserted 0 below minimum 1
```

Temp-artifact stale-window fallback smoke:

```text
tmpdir: /tmp/tmp.TIwNFVt1dJ
wide old-window run: exit 0, health success, fetched 2, inserted 2, chunks_written 2
narrow current-window run: exit 1, health failure, fetched 0, inserted 0, chunks_written 2
narrow context recent_news_chunks: 0
narrow problem: context recent news chunks 0 below minimum 1
```

Regression tests added:

- Duplicate capture-backed run fetches duplicate rows, inserts zero, rebuilds
  existing chunks, and fails health.
- Old capture-backed fallback chunks outside the current provider window fail
  health even when `chunks_written` is nonzero.

## Not Done

- Did not edit crontab, systemd timers, runner config, symlinks, or host runtime
  config.
- Did not run production news ingestion or mutate production news stores.
- Did not mutate Qdrant, Redis, production DBs, memory stores, source PDFs, gold
  labels, extraction prompts, parser routing, model/GPU config, backfills, or
  migrations.
- Did not push, merge, or mutate GitHub.

## Remaining Risk

This is validated with temp SQLite stores and capture fixtures. A real scheduled
run still depends on live provider/network behavior and the production artifact
root, but a zero-fetch, zero-upsert, or stale-window fallback outcome now fails
health by default instead of reporting success.
