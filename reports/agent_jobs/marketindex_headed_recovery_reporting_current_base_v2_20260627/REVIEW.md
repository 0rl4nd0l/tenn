# Review

```json
{
  "status": "SUCCESS",
  "work_log": {
    "assumptions": [
      "Issue #279 scope is operator-facing report clarity without changing MarketIndex blocking policy.",
      "Live runtime/backfill validation is out of scope for this task card."
    ],
    "sources_used": [
      "git diff",
      "AGENTS.md",
      "docs/README.md",
      "docs/entrypoints.md",
      "docs/dev_flow/REPO_PATH_OWNERSHIP_AND_WORK_PRESERVATION.md"
    ],
    "files_read": [
      "financial-engine_v2/scripts/full_history_ticker_sync.py",
      "financial-engine_v2/scripts/resume_pending_downloads.py",
      "financial-engine_v2/scripts/marketindex_recovery_reporting.py",
      "scripts/backfill_missing_universe_announcements.py",
      "financial-engine_v2/scripts/test_full_history_ticker_sync_env.py",
      "financial-engine_v2/scripts/test_marketindex_recovery_reporting.py",
      "financial-engine_v2/scripts/test_resume_pending_extraction_failures.py",
      "scripts/test_backfill_missing_universe_announcements.py"
    ],
    "files_modified": [
      "financial-engine_v2/scripts/resume_pending_downloads.py",
      "financial-engine_v2/scripts/test_resume_pending_extraction_failures.py",
      "financial-engine_v2/scripts/test_full_history_ticker_sync_env.py"
    ],
    "validation_checks": [
      "uv run --with pytest pytest -q financial-engine_v2/scripts/test_marketindex_recovery_reporting.py financial-engine_v2/scripts/test_full_history_ticker_sync_env.py financial-engine_v2/scripts/test_resume_pending_extraction_failures.py scripts/test_backfill_missing_universe_announcements.py",
      "uv run --with ruff ruff check <touched python files>",
      "python3 -m py_compile <touched python files>",
      "git diff --check"
    ]
  },
  "result": {
    "critical": [],
    "warnings": [],
    "suggestions": [
      {
        "file": "financial-engine_v2/scripts/resume_pending_downloads.py",
        "location": "MarketIndex HTTP 403 report sample",
        "issue": "When a document row has a blank source_url, the report sample should keep the actual request URL from the HTTP exception.",
        "fix_example": "Use getattr(row, \"source_url\", \"\") or request_url and cover it with a focused 403 test."
      },
      {
        "file": "financial-engine_v2/scripts/resume_pending_downloads.py",
        "location": "Standalone resume report initialization",
        "issue": "Reports should include existing blocked_marketindex_* rows for requested tickers, not only blockers created during the current run.",
        "fix_example": "Load existing MarketIndex blocker rows into the summary before the pending-empty-pdf processing loop and cover the helper with a focused test."
      },
      {
        "file": "financial-engine_v2/scripts/test_full_history_ticker_sync_env.py",
        "location": "Pipeline service test stub",
        "issue": "The test stub should not overwrite an already-imported real app.services.pipeline module for the rest of the pytest process.",
        "fix_example": "Patch sys.modules with a local pipeline stub only while loading full_history_ticker_sync.py."
      }
    ]
  }
}
```

The suggestions were applied and revalidated.
