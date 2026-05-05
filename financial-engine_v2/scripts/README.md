# Financial Engine V2 scripts

This folder contains runtime launchers, ingestion CLIs, analysis tools, commentary
utilities, recovery tooling, and test helpers.

For canonical backend startup, use:

- `scripts/run_local_backend.sh`

For the repo-wide canonical entrypoint rules, see:

- `../docs/entrypoints.md`

## Runtime and operator launchers

- `run_local_backend.sh`
  - canonical backend launcher for local/agent use
- `run_backend.sh`
  - legacy/direct backend launcher
- `run_worker.sh`
  - celery worker launcher
- `cockpit_tui.py`
  - cockpit terminal launcher
- `cockpit_serve.py`
  - cockpit web-serving entrypoint
- `cockpit_web.py`
  - cockpit web wrapper
- `reset_env.sh`
  - cleanup/reset helper
- `smoke_local.sh`
  - local smoke check
- `../../scripts/cockpit_routing_smoke.py`
  - backend Cockpit routing/provenance smoke check for API-only and metadata regressions
- `status.sh`
  - process/runtime status helper

## Ingestion and backfill

- `ingest_ticker.py`
- `full_history_ticker_sync.py`
- `daily_asx_all_announcements_action.py`
- `daily_asx_marketwide_action.py`
- `daily_marketindex_action.py`
- `download_pdfs.py`
- `marketindex_download_pdfs.py`
- `marketindex_ingest.py`
- `resume_pending_downloads.py`
- `update_ticker_financials.py`
- `rebuild_ticker_dataset.py`
- `rebuild_ticker_financials_from_docs.py`

## Extraction and embedding

- `extract_doc.py`
- `run_batch_extract.py`
- `run_extraction_backlog.py`
- `audit_extraction_backlog.py`
- `monitor_extraction.py`
- `embed_docs_to_qdrant.py`
- `re_embed_docs.py`
- `rebuild_rag_qdrant_index.py`
- `verify_vector_baseline.py`
- `inspect_qdrant_collection.py`
- `inspect_extraction_provenance.py`

## Commentary and framework ingestion

- `ingest_transcript.py`
- `promote_staged_commentary.py`
- `run_transcript_daemon.py`
- `resource_library_workflow.py`
- `extract_investment_frameworks.py`
- `preprocess_investment_pdfs.py`

## Analysis, evaluation, and reporting

- `run_analysis.py`
- `batch_analyse.py`
- `announcement_reaction_report.py`
- `generate_weekly_intelligence_pack.py`
- `evaluate_rag_stability.py`
- `verify_fixture_metrics.py`
- `validate_analysis_report.py`
- `export_financial_snapshot.py`
- `run_system_analyzer.py`

## Recovery and maintenance

- `recover_marketindex_headed.py`
- `cleanup_asx_docs_payloads.py`
- `cleanup_legacy_importance_mirror.py`
- `rename_document_files.py`
- `ticker_quarantine.py`
- `validate_ticker.py`

## Tests and support tooling

- `test_*.py`
  - script-surface regression and smoke coverage
- `conftest.py`
  - shared pytest fixtures/hooks for this folder
- `_run_metadata.py`
  - provenance helper for long-running CLIs

## Archive

Historical snapshots live under `scripts/archive/`.
