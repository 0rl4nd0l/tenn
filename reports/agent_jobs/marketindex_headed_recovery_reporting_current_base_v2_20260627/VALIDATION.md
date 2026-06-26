# Validation

## Passed

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/marketindex_headed_recovery_reporting_current_base_v2_20260627.md`
- `python3 scripts/agent_job_registry.py check-overlap --repo-root . docs/agent_tasks/marketindex_headed_recovery_reporting_current_base_v2_20260627.md`
- `uv run --with pytest pytest -q financial-engine_v2/scripts/test_marketindex_recovery_reporting.py financial-engine_v2/scripts/test_full_history_ticker_sync_env.py financial-engine_v2/scripts/test_resume_pending_extraction_failures.py scripts/test_backfill_missing_universe_announcements.py`
  - Result: `17 passed, 1 warning`
  - Warning: pytest config option `asyncio_default_fixture_loop_scope` unknown in the ephemeral pytest environment
- `uv run --with ruff ruff check financial-engine_v2/scripts/full_history_ticker_sync.py financial-engine_v2/scripts/marketindex_recovery_reporting.py financial-engine_v2/scripts/resume_pending_downloads.py financial-engine_v2/scripts/test_full_history_ticker_sync_env.py financial-engine_v2/scripts/test_marketindex_recovery_reporting.py financial-engine_v2/scripts/test_resume_pending_extraction_failures.py scripts/backfill_missing_universe_announcements.py scripts/test_backfill_missing_universe_announcements.py`
- `python3 -m py_compile financial-engine_v2/scripts/full_history_ticker_sync.py financial-engine_v2/scripts/marketindex_recovery_reporting.py financial-engine_v2/scripts/resume_pending_downloads.py financial-engine_v2/scripts/test_full_history_ticker_sync_env.py financial-engine_v2/scripts/test_marketindex_recovery_reporting.py financial-engine_v2/scripts/test_resume_pending_extraction_failures.py scripts/backfill_missing_universe_announcements.py scripts/test_backfill_missing_universe_announcements.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/marketindex_headed_recovery_reporting_current_base_v2_20260627.md`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/marketindex_headed_recovery_reporting_current_base_v2_20260627.md`

## Not Run

- Live backfill, MarketIndex headed recovery, browser automation, service start,
  DB mutation, and runtime smoke checks. These were hard-stopped by task scope.
