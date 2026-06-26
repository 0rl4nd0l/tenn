## Summary

- add shared MarketIndex headed-recovery report metadata helper
- expose `marketindex_headed_recovery` and `requires_headed_recovery_count` in resume/full-history report surfaces
- seed standalone resume reports from existing `blocked_marketindex_*` rows
- promote fresh child full-history recovery metadata into the missing-universe wrapper report
- add focused tests for the new report contract

Closes #279.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/marketindex_headed_recovery_reporting_current_base_v2_20260627.md`
- `python3 scripts/agent_job_registry.py check-overlap --repo-root . docs/agent_tasks/marketindex_headed_recovery_reporting_current_base_v2_20260627.md`
- `uv run --with pytest pytest -q financial-engine_v2/scripts/test_marketindex_recovery_reporting.py financial-engine_v2/scripts/test_full_history_ticker_sync_env.py financial-engine_v2/scripts/test_resume_pending_extraction_failures.py scripts/test_backfill_missing_universe_announcements.py`
- `uv run --with ruff ruff check financial-engine_v2/scripts/full_history_ticker_sync.py financial-engine_v2/scripts/marketindex_recovery_reporting.py financial-engine_v2/scripts/resume_pending_downloads.py financial-engine_v2/scripts/test_full_history_ticker_sync_env.py financial-engine_v2/scripts/test_marketindex_recovery_reporting.py financial-engine_v2/scripts/test_resume_pending_extraction_failures.py scripts/backfill_missing_universe_announcements.py scripts/test_backfill_missing_universe_announcements.py`
- `python3 -m py_compile financial-engine_v2/scripts/full_history_ticker_sync.py financial-engine_v2/scripts/marketindex_recovery_reporting.py financial-engine_v2/scripts/resume_pending_downloads.py financial-engine_v2/scripts/test_full_history_ticker_sync_env.py financial-engine_v2/scripts/test_marketindex_recovery_reporting.py financial-engine_v2/scripts/test_resume_pending_extraction_failures.py scripts/backfill_missing_universe_announcements.py scripts/test_backfill_missing_universe_announcements.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/marketindex_headed_recovery_reporting_current_base_v2_20260627.md`

## Runtime Proof

Report-contract validation passed. Live MarketIndex recovery, live backfill,
browser automation, service start, and DB mutation were intentionally not run.
Runtime functionality status is `PARTIAL` until a future live run produces a
fresh report with the new fields.
