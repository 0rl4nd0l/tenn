# Nightly News Ticker Universe Input Repair

Issue: #114

## Result

The missing canonical ticker universe input was restored at:

`financial-engine_v2/data/raw/asx_ticker_universe.txt`

Source evidence:

- `/mnt/nvme/tenn/financial-engine_v2/data/raw/asx_ticker_universe.txt`
- `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/raw/asx_ticker_universe.txt`
- Both source copies had SHA-256
  `042b6b799c24ecbcf0c94f73ac94753e90d35f8282cd10205c17a2f7f8479cf9`
  and `376` lines.

The restored canonical copy has the same SHA-256 and line count. The fetch
dry-run resolved `tickers_count=375`, because one line is a comment.

## Validation

`fetch_daily_news.py --providers newspaper4k --since-hours 36 --lane high_precision --dry-run`
exited `0` and printed a non-zero ticker count.

No live fetch, Qdrant sync, SQLite news refresh, memo backfill, or scheduler
mutation was performed.
