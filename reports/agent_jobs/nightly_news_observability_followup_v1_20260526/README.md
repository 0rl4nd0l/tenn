# Nightly News Observability Follow-Up

Issue: #112

## Result

`financial-engine_v2/scripts/nightly_news.sh` now:

- opens the nightly log before venv checks;
- tees stdout and stderr into the log;
- writes `nightly_news_<stamp>.status.json` on success or failure;
- records phase statuses for initializing, fetch, sync, memo, memo_backfill,
  and finish;
- passes `--tickers-file` explicitly to the fetch command;
- supports `NIGHTLY_NEWS_DRY_RUN=1` and `NIGHTLY_NEWS_LOG_DIR=...` for no-write
  validation.

## Validation

Success smoke:

- Command shape: `NIGHTLY_NEWS_LOG_DIR=/tmp/... NIGHTLY_NEWS_DRY_RUN=1 bash financial-engine_v2/scripts/nightly_news.sh`
- Result: exit `0`, status `success`, fetch `success`, sync/memo skipped by
  dry-run, finish `success`.

Failure smoke:

- Command shape: `NIGHTLY_NEWS_LOG_DIR=/tmp/... NIGHTLY_NEWS_DRY_RUN=1 NEWS_TICKERS_FILE=/tmp/tenn-missing-asx-ticker-universe.txt bash financial-engine_v2/scripts/nightly_news.sh`
- Result: exit `1`, status `failure`, failed phase `fetch`, traceback present
  in the log.

No live fetch, Qdrant sync, SQLite news refresh, memo backfill, cron edit, or
systemd edit was performed.
