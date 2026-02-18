# MarketIndex Architecture Snapshot (Legacy)

Status: archived legacy reference. Active runtime moved to `financial-engine_v2`.

Date: 2026-02-17  
Checkpoint: `scripts/archive/system_checkpoint_20260217_212812`

## System Topology

1. Ingestion
- Script: `scripts/test_marketindex.py`
- Source: `https://www.marketindex.com.au/asx/announcements`
- Output: `data/raw/marketindex_announcements.json`

2. PDF Download + Reliability Controls
- Script: `scripts/download_marketindex_pdfs.py`
- Input: announcements JSON
- Output PDFs: `data/pdfs`
- Output report: `reports/pdf_download_report.json`
- Reliability controls:
  - Headed-only policy (`--headless` rejected with exit code `2`)
  - One secondary recovery pass for unresolved rows (`--null-retry-delay-seconds`, default `15`)
  - Quality gate:
    - `--min-download-count` (default `5`)
    - `--min-success-ratio` (default `0.35`)
    - Fail only when both are below threshold (exit code `3`)

3. Daily Orchestration
- Script: `scripts/daily_marketindex_action.py`
- Runs ingestion, then download
- Output daily report: `reports/daily_marketindex_action_report.json`
- Config validation:
  - `--headless-download` is blocked early as `failed_config` with exit code `2`

## CLI Contract (Current)

Downloader (`scripts/download_marketindex_pdfs.py`)
- `--input`
- `--output-dir`
- `--report`
- `--limit`
- `--overwrite`
- `--headless` (unsupported; exits `2`)
- `--min-download-count` (default `5`)
- `--min-success-ratio` (default `0.35`)
- `--null-retry-delay-seconds` (default `15`)

Daily runner (`scripts/daily_marketindex_action.py`)
- `--python`
- `--ingest-script`
- `--download-script`
- `--announcements-file`
- `--pdf-dir`
- `--download-report`
- `--daily-report`
- `--download-limit`
- `--overwrite-pdfs`
- `--headless-download` (unsupported; early `failed_config`, exit `2`)
- `--skip-download`
- `--min-download-count` (default `5`)
- `--min-success-ratio` (default `0.35`)
- `--null-retry-delay-seconds` (default `15`)

## Report Schema (Downloader)

Top-level fields include:
- `total_processed`
- `downloaded`
- `skipped`
- `failed`
- `candidate_total`
- `success_ratio`
- `quality_gate`
  - `min_download_count`
  - `min_success_ratio`
  - `passed`
  - `reason` (when failed)
- `secondary_pass`
  - `attempted`
  - `unresolved_initial`
  - `recovered_links`
  - `remaining_unresolved`
- `results[]`

## Stable Status Semantics

- `downloaded`
- `skipped_exists`
- `skipped_unavailable` (typically 404/unavailable source doc)
- `skipped_no_candidate_link_after_retry`
- `failed_fetch`
- `failed_invalid_pdf_response`
- `failed_unknown`

## Latest Full-Batch Baseline

Latest full run against 503 announcements:
- `downloaded=460`
- `skipped=43`
- `failed=0`
- `candidate_total=503`
- `success_ratio=0.9145129224652088`
- `quality_gate.passed=true`

Reference report:
- `reports/pdf_download_report.json`
