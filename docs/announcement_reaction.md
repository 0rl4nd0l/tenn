# Announcement Reaction Report

`financial-engine_v2/scripts/announcement_reaction_report.py` joins recent rows in `documents` with close prices from `GET /api/price` and writes a JSON report of post-announcement returns.

The script is a standalone CLI. Cockpit does not call it. It does reuse `cockpit.integrations.backend_api.BackendApiClient` and the `COCKPIT_BACKEND_API_URL` default.

## Run

From `financial-engine_v2`, with that directory on `PYTHONPATH` (the `cockpit` package lives there; running the file only puts `scripts/` on `sys.path`):

```bash
cd financial-engine_v2
PYTHONPATH=. python3 scripts/announcement_reaction_report.py \
  --ticker BHP,CBA \
  --doc-class periodic \
  --days-back 45 \
  --range 1y \
  --interval 1d \
  --output reports/announcement_reaction_bhp_cba.json
```

The local API must already be listening. The CLI does not start it. In isolated mode that is `scripts/run_local_backend.sh` (see `financial-engine_v2/README.md`).

| Flag | Default | Behavior |
| --- | --- | --- |
| `--database-url` | `DATABASE_URL` or `sqlite:///./data/fe_local.db` | Read URL. Relative SQLite paths resolve under `financial-engine_v2/`. Other schemes are passed through. |
| `--api-base-url` | `COCKPIT_BACKEND_API_URL` or `http://localhost:8000` | Price API origin. A missing scheme becomes `http://`. |
| `--exchange` | `ASX` | Uppercased. Empty becomes `ASX`. |
| `--range` | `1y` | Sent as the `range` query parameter. The API's own default is `1mo` when the parameter is omitted. |
| `--interval` | `1d` | Sent as the `interval` query parameter. |
| `--days-back` | `45` | Keep rows with `published_at >=` UTC now minus this many days. Values below `1` become `1`. |
| `--limit` | `250` | SQL `LIMIT` applied before `--ticker` and `--doc-class`. Values below `1` become `1`. |
| `--top` | `20` | How many `top_movers` to keep. Values below `1` become `1`. |
| `--ticker` | empty | Comma-separated tickers, uppercased, applied after the SQL limit. |
| `--doc-class` | empty | Comma-separated classes, lowercased, applied after the SQL limit. |
| `--output` | `reports/announcement_reaction_report_<local YYYYMMDD_HHMMSS>.json` | Relative paths resolve under `financial-engine_v2/`. Parent directories are created. |

The filename clock is local `datetime.now()`. `generated_at` inside the file is UTC.

## Which documents are scored

SQL, ordered by `published_at DESC, document_id DESC`:

```sql
select document_id, ticker, doc_class, doc_subtype, published_at, title
from documents
where ticker is not null
  and trim(ticker) <> ''
  and published_at is not null
  and published_at >= :since_iso
```

`:since_iso` is `datetime.now(timezone.utc) - days_back` in `isoformat()` form (`+00:00` offset). The comparison is the database's native comparison against that string.

After that limit, `--ticker` and `--doc-class` drop rows in Python. A request such as `--limit 1 --ticker CBA` can scan zero documents when the single newest row is a different ticker. `documents_scanned` counts rows that remain after those filters.

## Price lookup

One `GET {api-base-url}/api/price` per remaining ticker, timeout 15 seconds. Query parameters are uppercased `ticker` and `exchange`, plus `range` and `interval`.

`backend/app/api/routes.py` builds a `MarketPriceProvider` and returns its payload. `ValueError` becomes HTTP 400. `MarketPriceProviderError` becomes HTTP 502. The client stores `detail` in `ticker_price_errors`. Connection failures store the exception text. A payload with no usable closes stores `no close series returned`. Any of these skip every document for that ticker. Other tickers still run.

The provider calls Yahoo chart `/v8/finance/chart/{symbol}` with `includePrePost=false`, `events=div,splits`, and `User-Agent: Mozilla/5.0`. It tries `query1.finance.yahoo.com`, then `query2.finance.yahoo.com` when the configured host fails. The error that is raised is the last failure: a 429 on the first host followed by HTTP 500 on the second is reported as HTTP 500. A chart `error.description` is raised as-is (`No data found`, for example).

Symbol rules (`MarketPriceProvider._normalize_symbol`):

- Blank ticker, range, or interval raises `ValueError` (`ticker is required`, `range is required`, `interval is required`).
- A ticker that already contains `.` is uppercased and used as-is (`bhp.ax` stays `BHP.AX` on any exchange).
- Otherwise the exchange suffix is `ASX -> .AX`, `LSE -> .L`, `TSX -> .TO`, `HKEX -> .HK`. `NYSE`, `NASDAQ`, and unknown exchanges add no suffix.
- An empty exchange string is treated as `ASX`.

`Settings` does not define `market_data_base_url` or `market_data_timeout_seconds`. The route therefore uses `https://query1.finance.yahoo.com` and a 20 second provider timeout. Those names are not read from the environment.

Returned history rows need a parseable `timestamp` and a numeric `close`. `Z` offsets are accepted. Naive timestamps are treated as UTC. The same timestamp keeps the last close in the payload. Rows are then sorted by time.

## How a return is measured

The anchor is the last bar with `timestamp <= published_at`. From that close, `ret_1d`, `ret_5d`, and `ret_20d` are the closes 1, 5, and 20 bars later:

```text
((later_close / anchor_close) - 1) * 100
```

With `--interval 1d` those bars are the bars Yahoo returned (typically sessions), so a missing session does not appear as a flat day. A horizon past the end of the series is JSON `null`. The anchor time and anchor close are the bar's timestamp and close. `published_at` itself is re-parsed; `Z` is accepted and naive values are treated as UTC.

The document is left out of `reaction_rows` when:

- `published_at` does not parse
- the announcement is before the first bar
- the anchor close is `0`

A row whose forward closes are missing stays in `reaction_rows` with null returns. `top_movers`, `summary_by_doc_class`, and `summary_by_ticker` keep only rows whose `ret_1d` is a float. Movers are the largest absolute `ret_1d`, truncated to `--top`. Summaries sort by average absolute `ret_1d` and include `count`, `avg_ret_1d`, `avg_abs_ret_1d`, and `positive_ratio` (`ret_1d > 0`).

`doc_class` in the report is stripped and lowercased. An empty class becomes `unknown`.

## Output and exit codes

Top-level keys: `generated_at`, `parameters`, `documents_scanned`, `tickers_scanned`, `reaction_rows`, `ticker_price_errors`, `top_movers`, `summary_by_doc_class`, `summary_by_ticker`.

| Outcome | Exit | Report file |
| --- | --- | --- |
| Report written, including when every ticker has a price error | `0` | written |
| `cockpit` cannot be imported | `1` | not written |
| SQLite path cannot be opened, or `documents` is missing | `1` | not written |

Price errors are data in `ticker_price_errors`, not a failed process. The stdout line is:

```text
[announcement-reaction] wrote <path> (documents=N, reactions=N, tickers=N, price_errors=N)
```

## Pitfalls

- `--limit` runs before `--ticker` and `--doc-class`. Raise the limit when a filter looks empty.
- `--days-back 45` with `--range 1mo` (or a short series) leaves `ret_5d` and `ret_20d` null for older announcements. The CLI default range is `1y` so the forward bars usually exist; the API default of `1mo` does not apply unless you override `--range`.
- `sqlite:///:memory:` is rewritten to a file path under `financial-engine_v2/` because the path does not start with `/`.
- A relative `--database-url` such as `sqlite:///./data/fe_local.db` always resolves from `financial-engine_v2`, including when the shell cwd is elsewhere.
- One failed price call drops the whole ticker. An empty `history` does that with `no close series returned`.

## Check

```bash
cd financial-engine_v2
python3 -m unittest scripts/test_announcement_reaction_report.py scripts/test_market_price_provider.py
```

The reaction tests cover duplicate timestamps (last close wins), the 1-bar and 5-bar percent math, a null 20-bar horizon, and an announcement dated before the series.
