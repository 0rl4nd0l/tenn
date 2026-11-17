# News Ingestion Throughput Profile

Job: `news_ingestion_throughput_profile_and_optimise_v1_20260527`
Related issue: #123
Lane: Evaluation
Mode: AUDIT ONLY
Generated: 2026-06-01T20:27:02+10:00

## Decision

This issue can advance as report-only, but product optimisation is not yet
safe to claim. The no-write probes show the dry-run plan, projection target
builder, and scratch SQLite fallback rebuild are fast on copied local SQLite
artifacts, but the current 36-hour window has zero eligible articles, Qdrant is
unreachable from this session, and embedding/upsert plus real memo
dispatch/wait/backfill require write-capable paths that were not approved by
this audit-only task.

## Measured No-Write Results

| Probe | Input | Time | Throughput | Result |
| --- | --- | ---: | ---: | --- |
| Fetch dry-run plan | 375 tickers, newspaper4k daily profile, `/tmp` output paths | 0.08s | 4,687 tickers/s plan-only | PASS, no fetch/write performed |
| Loader dry-run, 36h | copied SQLite artifact, `--since-hours 36` | 1.18s | 0 articles / 0 chunks | PASS, but no eligible current-window data |
| Loader dry-run, full copied DB | copied SQLite artifact, all eligible articles | 2.31s | 97.4 articles/s, 1,903.5 chunks/s | PASS for projection build; Qdrant diff unavailable |
| SQLite fallback scratch rebuild | copied SQLite artifact to `SCRATCH_TMP/news.sqlite` | 2.052s | 109.6 articles/s, 2,141.8 chunks/s | PASS on scratch output only |

Full copied-DB dry-run counts:
- eligible articles: 225
- eligible chunks: 4,397
- theoretical embed/upsert batches at batch size 64: 69
- memo-eligible articles: 212
- memo-skipped articles: 13
- memo dispatch plan, full copied DB: would dispatch 225 selected articles,
  with 212 missing memos and 13 skipped articles if real dispatch were approved
- Qdrant diff: `unavailable`, connection refused on `127.0.0.1:6333`

## Phase Matrix

| Phase | Current evidence | Status |
| --- | --- | --- |
| Wrapper setup/status | `nightly_news.sh` creates log/status/summary paths and phase fields; `bash -n` passed. | PASS static |
| Fetch plan | `fetch_daily_news.py --dry-run` resolved 375 tickers and newspaper4k daily options. | PASS no-write |
| Fetch/parse/store live throughput | Requires real provider fetch and SQLite writes. | DATA_MISSING, not run |
| Projection build | Full copied-DB loader dry-run built 225 article / 4,397 chunk target in 2.31s. | PASS no-write |
| Embedding | Loader dry-run returns before probe embedding and batch embedding. | DATA_MISSING, not run |
| Qdrant diff/upsert/delete | Dry-run attempted diff, but Qdrant connection was refused; upsert/delete are write paths. | DATA_MISSING / blocked |
| SQLite fallback refresh | Scratch rebuild on `/tmp` copy wrote 4,395 chunks in 2.052s. | PASS scratch-only; live write path not run |
| Memo dispatch/wait | Selection-only plan on copied DB found 225 would-dispatch articles for full corpus; 36h window is empty. | PASS plan-only; real dispatch DATA_MISSING |
| Retention cleanup | Candidate inspection found no local `reports/ops_checks/nightly` directory in this worktree. | PASS read-only; live cleanup not run |

## Blockers

- The isolated worktree has no local newspaper4k/backend venvs. The probes used
  existing shared venv interpreters read-only.
- Qdrant at `127.0.0.1:6333` was unavailable, so current Qdrant diff and
  skip-clean-upsert candidate counts were not measured.
- The copied local SQLite artifact has no eligible articles in the last 36
  hours, so the current nightly-window throughput baseline remains
  `DATA_MISSING`.
- Live fetch, live sync, memo dispatch/wait/backfill, and retention cleanup are
  write-capable paths and were not run under this audit-only task. SQLite
  fallback was measured only on scratch `/tmp` outputs.

## Follow-Ups

- Add timing fields to the nightly wrapper and loader summary only under a
  separate safe-extension task card.
- Add a no-dispatch/dry-run mode to `backfill_missing_news_memos.py` before
  profiling memo selection safely.
- Run an approved bounded live sync only after Qdrant/backend readiness and
  store-mutation approval are explicit.

## Boundaries

No source code, DB, Qdrant, news store, memory store, runtime config, scheduler,
model/GPU config, parser, prompt, gold label, or canonical financial truth was
mutated. Temporary copies/log paths were under scratch temp directories and
host-local absolute paths were redacted from committed artifacts.
