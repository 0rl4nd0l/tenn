# Change Impact Log

Use this file to track code changes, expected behavior impact, verification, and rollback notes.

## Entry Template

### Change ID: YYYYMMDD-<short-name>
- Date:
- Author:
- Scope:
- Files:
- Why:
- Expected impact:
- Risk level: low | medium | high
- Validation commands:
- Rollback plan:
- Observed issues after deploy:

---

### Change ID: 20260219-traceability-and-safety-fixes
- Date: 2026-02-19
- Author: Codex
- Scope: reliability + traceability
- Files:
  - `financial-engine_v2/backend/app/providers/asx_provider.py`
  - `financial-engine_v2/backend/app/services/announcement_importance.py`
  - `financial-engine_v2/cockpit/ui/app.py`
  - `financial-engine_v2/scripts/_run_metadata.py`
  - `financial-engine_v2/scripts/asx_enrichment_sweep_action.py`
  - `financial-engine_v2/scripts/daily_asx_all_announcements_action.py`
  - `financial-engine_v2/scripts/daily_asx_marketwide_action.py`
  - `financial-engine_v2/scripts/daily_marketindex_action.py`
  - `financial-engine_v2/scripts/full_history_ticker_sync.py`
  - `financial-engine_v2/scripts/resume_pending_downloads.py`
  - `financial-engine_v2/scripts/update_ticker_financials.py`
- Why: improve failure traceability and prevent known logic regressions.
- Expected impact:
  - run reports now include `run_metadata` (script, python, git branch/commit, dirty flag).
  - ticker discovery no longer stops on first empty year.
  - classification move/DB update has commit-failure compensation.
  - cockpit unknown action ids are handled with explicit log output.
- Risk level: medium
- Validation commands:
  - `python3 -m compileall -q financial-engine_v2/backend/app/providers/asx_provider.py financial-engine_v2/backend/app/services/announcement_importance.py financial-engine_v2/cockpit/ui/app.py financial-engine_v2/scripts`
- Rollback plan:
  - revert the files in this entry together so report schema + behavior stay consistent.
- Observed issues after deploy:
  - none recorded yet.

### Change ID: 20260219-a56b7a8-impact
- Date: 2026-02-19
- Author: 0rl4nd0l
- Scope: change-tracking workflow automation
- Files:
  - `financial-engine_v2/Makefile`
  - `reports/change_impact_log.md`
  - `scripts/log_change_impact.py`
  - `scripts/probe_all_system_tickers.py`
  - `scripts/run_asx_enrichment_chunked.py`
- Why: make it easy to trace regressions back to local code changes by standardizing impact-log entries.
- Expected impact: faster incident triage and clearer audit history for recent Codex/user edits.
- Risk level: medium
- Validation commands: `python3 financial-engine_v2/scripts/log_change_impact.py --help`; `python3 -m compileall -q financial-engine_v2/scripts/log_change_impact.py`; `python3 financial-engine_v2/scripts/log_change_impact.py`
- Rollback plan: revert `financial-engine_v2/scripts/log_change_impact.py`, remove `impact-log` target from `financial-engine_v2/Makefile`, and keep manual logging in `financial-engine_v2/reports/change_impact_log.md`.
- Observed issues after deploy:
  - none recorded yet.
