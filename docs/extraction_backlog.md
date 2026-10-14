# Extraction Backlog

SQLite-only tools for seeing which downloaded announcements still need extraction, grouping failed runs, and replaying `process_document`. They live in `financial-engine_v2/scripts/` and read `documents` plus `extraction_runs` directly.

Run them from `financial-engine_v2/` with the backend on `PYTHONPATH`. The scripts insert `backend/` themselves, so a plain `python3 scripts/...` invocation is enough when the process can import the backend.

```bash
cd financial-engine_v2
python3 scripts/audit_extraction_backlog.py \
  --database-url sqlite:////absolute/path/fe_local.db
python3 scripts/classify_extraction_failures.py \
  --database-url sqlite:////absolute/path/fe_local.db
ENABLE_EXTRACTION=true python3 scripts/run_extraction_backlog.py \
  --database-url sqlite:////absolute/path/fe_local.db \
  --ticker BHP --limit 50 --dry-run
```

`full_history_ticker_sync.py --audit-extraction-backlog` runs the audit and the classifier after sync and resume. It does not run `run_extraction_backlog.py`. A non-zero exit from either child marks that sync failed.

## Shared constraints

- `--database-url` must be `sqlite:///...`. A Postgres URL, `sqlite:///:memory:`, and a blank path raise `RuntimeError` before a report is written.
- The default URL is `settings.database_url` after `app.core.config` resolves a relative SQLite path against `financial-engine_v2/`. An explicit relative `--database-url` is resolved from the current working directory instead.
- A missing database file prints `Database not found` and exits `2`.
- `pdf_sha256` values that start with `blocked_marketindex_` are operational markers (`blocked_marketindex_403`, `blocked_marketindex_headed_required`), not downloaded files.

Selection uses the latest `extraction_runs` row per document (`created_at` descending). SQLite window functions are required.

## What each command counts

| Situation | Audit | Classifier | Runner |
| --- | --- | --- | --- |
| Downloaded, no extraction run | `downloaded_not_extracted` | omitted | selected |
| Downloaded, latest status `failed` | `latest_failed` | classified | selected |
| Downloaded, latest status `skipped` | omitted from both buckets | omitted (`status = 'failed'` only) | selected |
| Latest status `ok` | omitted | omitted | omitted |
| Empty `pdf_sha256` or `blocked_marketindex_*` | not counted as downloaded; a failed run on that row still increments `latest_failed` | classified when the latest run failed | omitted |

The audit scans every document. The runner and classifier accept repeated or comma-separated `--ticker` values. Age buckets on the audit use `published_at`, then `ingested_at`: `0_7d`, `8_30d`, `31_90d`, `91_365d`, `366d_plus`, or `unknown`.

### Audit

`audit_extraction_backlog.py` writes `financial-engine_v2/reports/extraction_backlog_audit.json`.

- `--sample-limit` defaults to `100` and caps each sample list. Values below `1` are raised to `1`.
- Exit `0` after a successful write. The command does not fail because the backlog is non-empty.

### Failure taxonomy

`classify_extraction_failures.py` writes `financial-engine_v2/reports/extraction_failure_taxonomy.json`.

Buckets, in first-match order, come from `classify_extraction_failure` in `backend/app/services/pipeline.py`:

| Category | Matched when the error text contains |
| --- | --- |
| `ocr_or_text_unavailable` | `empty text`, `no text`, `text unavailable`, `ocr`, `unable to extract text`, `could not extract text` |
| `parser_timeout` | `timeout`, `timed out`, `deadline exceeded`, `took too long` |
| `llm_invalid_json` | `invalid json`, `jsondecodeerror`, `expecting value`, `malformed json`, `could not parse json`, `json parse` |
| `provider_network` | `connection`, `connecterror`, `network`, `name resolution`, `dns`, `refused`, `temporarily unavailable`, `httpx`, `ssl` |
| `corrupted_pdf` | `not a pdf`, `corrupt`, `trailer not found`, `eof marker`, `pdfsyntaxerror`, `cannot open pdf`, `invalid pdf` |
| `unknown` | anything else, including an empty error |

The classifier passes each failed row's `error` and `structured_json` into that function. With no error text, a JSON object in `structured_json` is classified instead.

Defaults: latest failed run per document, `--limit 4000`, `--sample-per-class 5`. `--all-runs` classifies every failed run. `counts_by_category` always contains every bucket. Exit `0` when the report is written.

`process_document` does not assign `ocr_or_text_unavailable` for a PDF that simply extracts as empty text. That label appears only when the stored error text matches the tokens above.

## Replaying the backlog

`run_extraction_backlog.py` calls `process_document` on selected rows, newest `published_at` or `ingested_at` first. Default report: `financial-engine_v2/reports/run_extraction_backlog_report.json`.

```bash
cd financial-engine_v2
ENABLE_EXTRACTION=true python3 scripts/run_extraction_backlog.py \
  --database-url sqlite:////absolute/path/fe_local.db \
  --limit 1000 \
  --concurrency 2 \
  --max-retries 2 \
  --retry-delay-seconds 2 \
  --max-consecutive-failures 20
```

| Flag | Default | Behavior |
| --- | --- | --- |
| `--limit` | `1000` | Cap on selected rows. Values below `1` become `1`. |
| `--concurrency` | `2` | Thread pool size. Completion order drives the consecutive-failure counter. |
| `--max-retries` | `2` | Attempts per document. Values below `1` become `1`. |
| `--retry-delay-seconds` | `2` | Sleep is `delay * attempt` before another try. |
| `--max-consecutive-failures` | `20` | Stops scheduling after this many collected failures in a row. A collected success resets the counter. |
| `--with-embeddings` | off | Without the flag, the process sets `enable_embeddings` and `enable_qdrant` false for the run, then restores them. |
| `--dry-run` | off | Writes the report and a `backlog_sample` of at most 50 rows. Skips the health gate and `process_document`. |
| `--health-json` | repo `reports/research_engine_health.json` | Same default path as `scripts/generate_engine_health_snapshot.py`. |
| `--allow-warning` | off | Lets `overall_status=warning` through. |

`ENABLE_EXTRACTION` is not changed by the runner. `process_document` records `extraction_status=skipped` when extraction is disabled, and the runner treats every status other than `ok` as a failure. Local backend startup sets `ENABLE_EXTRACTION=false`; leave that unset or set it true before a replay, and keep `EXTRACT_MODEL` pointed at a model the host Ollama can serve. `.env.example` uses `llama3.1:8b`. The code default when the variable is unset is `llama3:latest`.

### How retries see errors

`process_document` catches extraction exceptions, stores them on `extraction_runs`, and returns `extraction_status=failed`. The runner then classifies the literal string `extraction_status_failed`, which is `unknown`, and retries until `--max-retries` is exhausted. The taxonomy of the stored Ollama or JSON error is visible to `classify_extraction_failures.py` after the run, not to this retry decision.

Exceptions that escape `process_document` (missing document, PDF open failure, database errors) use the exception text. Those retries run only for `provider_network`, `parser_timeout`, and `unknown`. `ocr_or_text_unavailable`, `llm_invalid_json`, and `corrupted_pdf` stop on that attempt. The report's `attempts` field on a failure is still the configured maximum.

On `stopped_early`, rows already sitting in the thread pool can still finish when the pool shuts down. Their `extraction_runs` writes are kept, and their results are left out of `processed`, `errors`, and `failure_categories`. `remaining_unprocessed` is `backlog_selected - processed` for collected results only. `errors` keeps at most 500 entries.

SQLite writes from concurrent `process_document` sessions can contend. `--concurrency 1` avoids that.

The runner's SQLite query and `process_document` use different connections. `process_document` writes through `settings.database_url`. Pass the same database the process already resolved, or the replay reads one file and writes another.

### Exit codes

| Code | When |
| --- | --- |
| `0` | No selected rows, a dry-run, or every collected document returned `ok`. An empty selection prints `[backlog] no documents to process` and does not write a report. |
| `1` | Any collected failure, including a run that stops early. |
| `2` | Database file is missing. |
| traceback | Non-SQLite URL, or the health gate raises `RuntimeError`. No backlog report is written. |

Health gate, for a non-dry-run:

- Missing snapshot file: warning on stderr, execution continues (`overall_status` `missing`).
- `healthy`: continues.
- `warning`: blocked unless `--allow-warning`.
- `degraded`, invalid JSON, or a status outside `healthy` / `warning` / `degraded`: blocked.

`assert_healthy` raises `RuntimeError` with `Health gate blocked execution: system degraded` or `system warning state`.
