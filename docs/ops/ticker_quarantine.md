# Ticker quarantine (full-history sync)

When running `full_history_ticker_sync.py` with a **ticker-universe file**, tickers that never return announcements and have no documents in the DB are treated as likely non-ASX symbols and are **quarantined**: they are written to a quarantine list and excluded from future universe runs.

## Purpose

- Avoid repeated no-op API calls for symbols that are not ASX-listed (e.g. LSE tickers in the universe, typos, or delisted codes).
- Only apply when the run is healthy and other tickers do return data, so we do not quarantine real companies when the fetch or API is broken.

## Where it lives

- **Quarantine list:** `financial-engine_v2/config/ticker_quarantine.json`
- **Helpers:** `financial-engine_v2/scripts/ticker_quarantine.py` (`load_quarantine`, `add_to_quarantine`, `save_quarantine`)
- **Document-level quarantine rules:** `financial-engine_v2/config/document_quarantine_rules.json`

## When a ticker is quarantined

All of the following must be true:

1. The run was started with **`--ticker-universe-file`** (not only `--ticker`).
2. The run **completed successfully** or was **interrupted** by the user (`status == success` or `status == interrupted`). Quarantine runs even when you stop the script (Ctrl+C / SIGTERM), so partial runs still quarantine no-announcement tickers.
3. **At least one other ticker** in the same run had **`found > 0`** (API returned data).
4. For this ticker: **`found == 0`** and **`existing_doc_count == 0`** (no announcements and no documents in DB).

So we **do not** quarantine when:

- The run failed for another reason (e.g. network or API down before any ticker succeeded).
- The ticker already has documents in the DB (e.g. already up to date).
- The run used only explicit `--ticker` (no universe file).
- Every ticker in the run had `found == 0` (no evidence the API was working).

## Behaviour in the sync script

- **Load (universe file only):** At start, the script loads the quarantine list and **excludes** any ticker in it from the run. It logs how many were excluded and a sample.
- **After a successful or interrupted run:** Tickers that meet the conditions above are **added** to the quarantine list (merged; existing entries are not duplicated). Newly added tickers are logged and written to `config/ticker_quarantine.json`. If you stop the script (Ctrl+C / SIGTERM), quarantine still runs before exit.

## Disabling quarantine

- **`--no-quarantine`**  
  Disables both: no filtering from the quarantine list when loading the universe, and no new tickers added to quarantine after the run.

## Manual control

- **Remove a ticker:** Edit `financial-engine_v2/config/ticker_quarantine.json` and delete the ticker from the `quarantined` array.
- **Inspect:** The same file lists all quarantined tickers plus `updated_at` and `reason`.

## Related

- Full-history sync: `financial-engine_v2/scripts/full_history_ticker_sync.py`
- Pipeline: `backend/app/services/pipeline.py` (`backfill_ticker_sync` returns `existing_doc_count` for quarantine logic)

## Document-level quarantine (announcement/PDF)

Ticker quarantine excludes whole symbols from universe sync.  
Document-level quarantine excludes specific announcements/PDFs for a ticker when the content is known to be non-representative for parent-level analysis.

Current policy:

- Ticker: `29M`
- Quarantined entity/topic: `EMR Capital / Golden Grove` subsidiary-level documents
- Rule file: `financial-engine_v2/config/document_quarantine_rules.json`

Enforcement points:

1. `backend/app/services/pipeline.py`
   - Discovery: quarantined announcements are not inserted.
   - Download: quarantined documents are marked `pdf_sha256=blocked_document_quarantine` and skipped.
2. `scripts/extract_financial_metrics.py`
   - PDF scan skips quarantined files before extraction.
   - Skipped files are emitted as context rows with `context_reason=document_quarantined`.

Control flags:

- `scripts/extract_financial_metrics.py --no-quarantine-rules` disables document-level filtering for one run.
- To re-include quarantined documents permanently, remove or narrow the corresponding rule in
  `financial-engine_v2/config/document_quarantine_rules.json`.
