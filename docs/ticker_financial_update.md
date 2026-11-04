# Ticker Financial Update

Operator path for one ticker: discover announcements, download PDFs, optionally extract, count `asx_periodic_financials` rows, and write a JSON report.

The implementation is `financial-engine_v2/scripts/update_ticker_financials.py`. Cockpit action `update_ticker_financials` and `financial-engine_v2/scripts/ingest_ticker.py` both call that script. `ingest_ticker.py` is a thin forwarder: it uppercases the ticker, forwards `--years`, `--report`, and `--dry-run`, and does not expose retry or zero-row flags.

## Commands

From `financial-engine_v2/`:

```bash
python3 scripts/update_ticker_financials.py --ticker BHP --years 5
python3 scripts/update_ticker_financials.py --ticker BHP --zero-rows-policy strict_fail
python3 scripts/update_ticker_financials.py --ticker BHP --dry-run
python3 scripts/ingest_ticker.py --ticker BHP --years 5 --no-process-documents
```

Defaults:

| Flag | Default | Constraint |
| --- | --- | --- |
| `--years` | `5` | Must be greater than 0. `0` or negative exits 1 with `--years must be > 0`. |
| `--max-backfill-retries` | `3` | Must be greater than 0. `0` or negative exits 1. |
| `--resume-max-retries` | `5` | Passed through to the resume script. The update script does not reject `0`. |
| `--resume-retry-delay-seconds` | `2.0` | Base delay for resume network retries. |
| `--process-documents` / `--no-process-documents` | process | Last flag wins. `ingest_ticker.py` appends `--no-process-documents` after `--process-documents` when both are set. |
| `--zero-rows-policy` | `warn` | `warn`, `auto_rebuild_fail`, or `strict_fail`. Any other value exits 2. |
| `--report` | `reports/financial_update_report.json` | Parent directory is created on a live run. |
| `--skip-resume-pending` | off | Skips the resume subprocess. |

Omitting `--ticker` exits 2. A blank or whitespace-only ticker exits 1. The symbol is stripped and uppercased.

Unknown flags exit 2. Dry-run exits 0. A live run exits 0 only when `status` is `success`, and exits 1 otherwise. The report file is written before that exit.

## What a live run does

1. Calls `backfill_ticker_sync(ticker, years, process_documents)`.
2. Unless `--skip-resume-pending`, runs `scripts/resume_pending_downloads.py` for documents whose `pdf_sha256` is empty or null.
3. Counts rows in `asx_periodic_financials` for the ticker.
4. Applies the zero-row policy.
5. Refreshes `cockpit_announcement_context` from the latest 40 `documents` rows.
6. Writes the report.

Raised exceptions from backfill are retried up to `--max-backfill-retries`. The sleep between attempts is `attempt * 2` seconds. Document-level errors returned inside the backfill payload are not retried.

The resume command gets `PYTHONPATH=backend` and `DATABASE_URL` when that variable was unset. Its report is `{report stem}_resume.json` next to the main report. Resume exits 1 when its own `totals.errors` is greater than 0, and the update then fails.

`auto_rebuild_fail` runs `scripts/rebuild_ticker_financials_from_docs.py --ticker … --limit 120 --force` only when the post-update row count is 0. That report is `{report stem}_rebuild.json`. A non-zero rebuild exit still passes the gate when the post-rebuild row count is greater than 0.

## Success rule

`status` is `success` only when all of these are true:

- Backfill returned a payload rather than raising on every attempt.
- `backfill.error_count` is 0. A missing key is treated as 0.
- The resume process exited 0, or resume was skipped.
- `quality_gate.passed` is true.
- `extraction_failures.total` is 0.

`extraction_failures.total` is `backfill.extraction_failed_count`. `backfill_ticker_sync` does not set that key, so on the live path this total stays 0. The unit test supplies the key; a live backfill does not.

`process_document` catches extractor exceptions, stores an `extraction_runs` row with `status=failed`, and returns `extraction_status=failed` without raising. Backfill still counts that document as `processed` and does not add it to `errors`. The update script never reads that return value. A live update can therefore exit 0 while new documents have failed extractions.

The resume phase does inspect `extraction_status`. A pending download whose extraction status is `failed` increments resume errors and makes the update fail. Documents that already have a `pdf_sha256` are not in that resume set.

MarketIndex headed-browser and HTTP 403 cases are stored as `pdf_sha256` markers and counted as skipped downloads. They do not increment `error_count`. An importance-classification error is stored on the backfill payload and does not change `status`.

## Zero-row policy

The row count is `select count(*) from asx_periodic_financials where ticker = ?`. A query exception is stored on `before.error` or `after.error` and the missing count is treated as 0.

| Policy | Zero rows after the update |
| --- | --- |
| `warn` (default) | `quality_gate.passed` stays true. A reason is recorded. Exit can still be 0. |
| `auto_rebuild_fail` | Rebuild runs. Exit 1 only when the count is still 0 afterward. The rebuilt count is `quality_gate.after_rows`, not `after.rows`. |
| `strict_fail` | `quality_gate.passed` is false and the process exits 1. |

`ingest_ticker.py` and the cockpit action do not pass `--zero-rows-policy`, so both use `warn`.

`ENABLE_EXTRACTION` defaults to true in `Settings`. `run_local_backend.sh` exports `ENABLE_EXTRACTION=false` for the API process only. When the update shell itself has `ENABLE_EXTRACTION=false`, `process_document` returns `extraction_status=skipped` and does not raise. That does not fail the update. With the default `warn` policy, zero financial rows can still be `status=success`.

## Database

On import, the update script changes the working directory to `financial-engine_v2/`. The row-count query uses `DATABASE_URL`, or `sqlite:///./data/fe_local.db` when it is unset. Backfill uses `Settings`, which turns a relative SQLite URL into an absolute path under `financial-engine_v2/` and, when `DATABASE_URL` is unset, opens `financial-engine_v2/data/fe_local.db`. After the import-time directory change, those two defaults are the same file.

`cockpit_announcement_context` is created in that database if it is missing. Each selected document stores the first PDF page, collapsed to 2000 characters. A missing PDF, a missing PyMuPDF import, or a SQL error is recorded on `announcement_context.error` and does not change the exit code. Dry-run does not write this table.

## Dry-run

`--dry-run` prints a plan JSON to stdout and does not call backfill, resume, rebuild, or announcement refresh. It does not write the report. It does query the row count, so `before.error` is populated when that query fails, and the process still exits 0.

The plan includes `resume_command` (null when resume is skipped) and `auto_rebuild_command`. The rebuild command is only a preview. Dry-run does not execute it.

## Cockpit

Action id: `update_ticker_financials`. The command is the update script with `--years` default 5, backfill retries 3, resume retries 5, resume delay 2.0 seconds, and `--process-documents`. `--skip-resume-pending` is added only when that argument is true. The report path defaults to `reports/financial_update_{ticker}_{id}.json`. Timeout is 7200 seconds. Python is `financial-engine_v2/.venv/bin/python`, then the parent `.venv`, then `sys.executable`.

The cockpit gate is separate from `--zero-rows-policy`:

- It runs only after the process status is `success`, the action is mutating, and this invocation is not a dry-run.
- It reads the `--report` file on the command. It does not read the resume or rebuild siblings.
- `after.rows <= 0` is a failure even when the script used `warn` and exited 0. The rebuilt count in `quality_gate.after_rows` is ignored.
- A missing or unreadable report fails the gate and is also logged as a warning.
- The result is a log line, `Quality gate: PASS` or `Quality gate: FAIL`. The stored job status stays the process status.

A mutating run is refused while another job in the heavy group is `queued` or `running`, has no `ended_at`, and started within 24 hours. The group is `full_history`, `update_ticker_financials`, `rebuild_ticker_financials`, `daily_marketindex`, `daily_asx_marketwide`, `asx_enrichment_sweep`, `resume_pending`, and `recover_headed`. The UI checks the 200 most recent jobs by `started_at`. Read-only mode blocks a mutating run that is not a dry-run. An already running cockpit task blocks every new action until it is killed.

## Tests

```bash
python3 -m unittest financial-engine_v2/scripts/test_update_ticker_financials_quality_gate.py
python3 -m unittest financial-engine_v2/scripts/test_cockpit_action_runtime_guards.py
```

The quality-gate tests mock backfill. They cover `warn` with zero rows, `auto_rebuild_fail` when the rebuild leaves zero rows, and a payload that sets `extraction_failed_count`.
