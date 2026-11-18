# Cockpit watchlist, alerts, and changes

Chat commands on the cockpit `c` screen. They run before normal chat. A plain-language phrase is rewritten into one of these commands only when the message does not already start with `/`.

State lives in the cockpit SQLite file from `memory.state_db`. The checked-in default is `~/.financial_engine_cockpit/state.db` (`config/cockpit.yaml`). `StateStore` expands `~` and creates the parent directory.

The chat thread id is fixed at `global-main`. The watchlist is global. Update history used by `/changes` is limited to that thread.

## Commands

| Input | Effect |
| --- | --- |
| `/watch`, `/watch list`, `/watch ls` | Print the watchlist. Bare `/watch` also prints usage. |
| `/watch add TICKER`, `/watch + TICKER`, `/watch a TICKER`, `/watch TICKER` | Insert the ticker. A second insert reports that it is already present. |
| `/watch remove TICKER`, `/watch rm`, `/watch del`, `/watch delete` | Delete one ticker. |
| `/watch clear`, `/watch reset` | Delete every watchlist row and report the count. |
| `/watch sync` | Run a one-year financial update for each listed ticker. Extra tokens are ignored. |
| `/alerts` | Evaluate the current watchlist. |
| `/alerts TICKER` | Evaluate one ticker, whether or not it is on the watchlist. |
| `/alerts thresholds`, `/alerts config`, `/alerts settings` | Print the numeric thresholds. |
| `/alerts help`, `/alerts h`, `/alerts ?` | Print usage and do not call the price API. |
| `/changes` | Show the latest successful update for the last ticker seen in a normal chat reply. |
| `/changes TICKER` | Same, for that ticker. Extra tokens are ignored. |

Examples:

```text
/watch add BHP
/watch bhp
watch csl
add rio to watchlist
/alerts
check alerts for bhp
/alerts thresholds
/changes BHP
what changed for bhp
/watch sync
```

## Ticker rules

Slash commands accept a ticker only when it is 2 to 5 letters after uppercasing. `BHP.AX` and `B` are rejected with `Expected 2-5 letters`.

A second `/watch` token that is not a known verb is an add when it matches that pattern. `/watch nope` stores `NOPE`. `/watch 12` and `/watch BHP.AX` are unknown commands. `/watch sync` does not fall through to that add path; the chat router matches it first.

Plain language uses the same 2-to-5-letter shape, then drops a fixed stopword list (`AN`, `FOR`, `ON`, `TO`, `LAST`, `WATCH`, and the other words in `conversation_commands.py`). `add AN to watchlist` stays a normal chat message. `/watch add AN` stores `AN`.

The first matching phrase wins, in this order: access status, web on/off, RAG on/off, SQL diagnostics on/off, watchlist sync/clear/list, watch remove, watch add, alerts, changes.

- `what changed for bhp alerts` becomes `/alerts BHP`.
- `show alerts and enable web` becomes `/request-access web`.
- `price bhp` and `analyse bhp` stay normal chat.
- `watch bhp earnings` becomes `/watch add BHP`.

## Where rows are stored

`watchlist_items` is keyed by ticker. Inserts use `insert or ignore`. Listing is `added_at` ascending with a limit of 200.

`/watch list`, `/alerts`, and `/watch sync` all use that 200-row read. A 201st older row remains in the table and is left out of those commands until an older row is removed.

`update_events` stores `/changes` history and the summary written by `/watch sync`. Listing is newest id first. `/changes` keeps only rows whose status normalizes to `success`. Stored `completed` counts as success. `failed` does not. Rows written on any thread other than `global-main` are invisible here.

`/changes` with no ticker reads `last_detected_ticker`. That value is set from a normal chat reply's evidence ticker. Slash commands do not update it. With no ticker, the reply is `changes requires a ticker.` With a ticker and no successful event, the reply tells you to run `update TICKER announcements now` and then `/confirm`.

## Alert inputs

`/alerts` calls `ToolRouter.get_price_state(ticker, deep_mode=False)`. That is `GET /api/price` through the cockpit backend client:

- `exchange=ASX`
- `range=3mo`
- `interval=1d`
- timeout 12 seconds

The same key, including a failed lookup, is cached for 20 seconds. Returns are computed from the full payload history. The 120-row compact copy is for display, not for these returns.

Close handling:

- Rows without a finite close are dropped.
- The same timestamp keeps the last close.
- `last_close` is the last history close when any close exists. `current.price` is used only when history has no close.
- `ret_Nd` is the percent change from the close `N` bars earlier to the last close. It needs `N + 1` closes. A zero base close makes that return `None`.
- `vol_20d_ann` uses the last 21 closes. It is the sample standard deviation of positive log returns, times `sqrt(252)`, times 100. It needs 21 closes and at least two usable log returns.
- `drawdown_from_63d_high` compares the last close with the max of the last 63 closes, or fewer when history is shorter. It can be `0` when the last close is the high.
- `ret_63d` needs 64 closes. A 3-month daily window often does not have that many bars, so the 63-day return is often missing. Drawdown can still fire on a shorter window. Alerts do not read `insufficient_history`.

`stale_data` is separate from the numeric thresholds. It is true when `current.market_time` is more than 96 hours old. The price provider fills that field from Yahoo `regularMarketTime`. Age of exactly 96 hours is fresh. A future timestamp is clamped to 0 hours and is fresh. A missing or unparseable market time is stale, with `data_age_hours` left empty.

## Thresholds and score

Defaults in `cockpit/core/alerts.py`:

| Check | Condition | Severity |
| --- | --- | --- |
| `ret_1d_move` | `abs(ret_1d) >= 3` | warning |
| `ret_20d_momentum` | `abs(ret_20d) >= 10` | warning |
| `high_volatility` | `vol_20d_ann >= 45` | warning |
| `drawdown_63d` | `drawdown_from_63d_high <= -12` | warning |
| `stale_data` | `stale_data is True` | critical |
| `price_error` | price state `ok` is false | critical |

Values equal to a threshold fire. A missing metric does not. There is no cockpit YAML key for these numbers. `/alerts thresholds` prints the four numeric rules and `stale_data = critical`. It does not print the 96-hour rule, so a fresh-looking price can still show `Price data stale (unknown)` when market time is absent.

A failed lookup returns only `price_error`. Other fields on that payload, including `stale_data`, are ignored. The message is the price state's `error` string, for example an HTTP 404 from `GET /api/price`.

Score starts at 0. For each fired alert, in the order 1-day, 20-day, volatility, drawdown, stale:

1. Replace the score with the greater of the current score and the severity weight: info `1`, warning `2`, critical `3`.
2. If the alert value is numeric, add `min(abs(value) / 100, 2)`.

The result is rounded to 3 decimal places. The unit-test state (`ret_1d=4.2`, `ret_20d=-11.5`, `vol_20d_ann=48`, `drawdown=-14.2`, stale age `120`) scores `4.2`. A lone price error scores `3.0`.

`/alerts` sorts tickers by that score, highest first. It prints at most 25 triggered tickers and at most 10 quiet tickers, then prints the thresholds again.

## `/watch sync`

For each ticker in the 200-row watchlist, in `added_at` order, cockpit runs action `update_ticker_financials` with:

- `ticker` set to that symbol
- `years=1`
- `process_documents=True`
- confirmation skipped
- the chat waiting until the job finishes

The action is mutating. `--read-only` blocks it. An already running job blocks it. A queued or running heavy job with no `ended_at`, started within 24 hours, also blocks it. Heavy jobs include `update_ticker_financials`, `full_history`, `rebuild_ticker_financials`, `daily_marketindex`, `daily_asx_marketwide`, `asx_enrichment_sweep`, `resume_pending`, and `recover_headed`. A blocked ticker is reported as `skipped (action did not start)` and the loop continues.

On each attempt that starts, cockpit writes an `update_events` row for `global-main`. Status comes from the newest 50 job rows whose action and ticker match. `success` is the job-runner status for exit code 0. The summary line includes that status, the new document count, and the after-sync freshness text.

## `/changes` market reaction

After the latest successful event, cockpit calls `GET /api/price` with `range=1y`, `interval=1d`, `exchange=ASX`, and a 15-second timeout. That is a wider window than `/alerts`.

It keeps the first 25 `new_announcements` rows, skips rows whose `published_at` does not parse, and prints the three largest absolute 1-day reactions. A 1-day reaction is the next daily close after the last close at or before `published_at`. A missing later bar is printed as `n/a`. If the price call fails, the announcement list is still shown and the reaction line carries the error text.

## Pitfalls

- Alerts need the backend API. A down API becomes one critical `price_error` per ticker and hides move or staleness detail.
- The 20-second price cache repeats that error until it expires.
- `/alerts` on an empty watchlist does not call prices. It tells you to `/watch add TICKER`.
- Stale data is critical even when returns are inside the numeric bands.
- Plain-language routing can steal a changes question when the text also contains `alert`, `web`, `rag`, or `sql`.
- `/watch sync` confirms nothing and can start a long `update_ticker_financials` run for every saved ticker.
- `/changes` does not see failed updates, other threads, or a ticker that was only mentioned in a slash command.
