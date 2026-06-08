# Release Notes: Phases A-C

This document summarizes the completed phased rollout up to Phase C.

## Phase A (commit `4c9b1ea`)
Title: `phase-a: stability fixes and heuristic-first resource workflow rollout`

Included:
- ASX discovery resilience for empty annual batches.
- Announcement-classification file/DB rollback safety.
- ASX enrichment classification coverage fix (deduped processed IDs).
- Conservative ASX sweep throttle defaults.
- Resource library workflow CLI added (heuristic default, LLM opt-in).
- README/playbook updates and rollout checklist.

Risk notes:
- Slower request throughput by design due to safer throttling defaults.
- Heuristic summaries are intentionally simple; review gate remains mandatory.

## Phase B (commit `797d46a`)
Title: `phase-b: add cockpit job cancellation and single-active-job guard`

Included:
- Active process tracking in job runner.
- Graceful terminate then hard kill fallback for cancellation.
- Cockpit-level single-active-job enforcement.
- "Kill Running Action" controls in Chat and Ops screens.
- Progress hints in cockpit logs for ticker/day sweep output.

Risk notes:
- Single-active-job policy may block parallel operator workflows by design.
- Cancellation behavior depends on subprocess termination handling.

## Phase C (commit `048ec9b`)
Title: `phase-c: add run metadata and ticker universe pacing controls`

Included:
- Shared run metadata helper (`scripts/_run_metadata.py`).
- `run_metadata` added to report payloads across ingestion/ops scripts.
- `full_history_ticker_sync.py` enhancements:
  - `--ticker-universe-file`
  - `--max-tickers`
  - `--ticker-delay-seconds`
  - `--ticker-delay-jitter-seconds`
  - per-ticker progress log output

Risk notes:
- Scripts now rely on `_run_metadata.py` being present in the repo.
- `full_history_ticker_sync.py` help/runtime requires dependencies (for example `httpx`).

## Post-Phase C rolling updates (current runtime)
Included:
- Public API expansion:
  - Added market price endpoint `GET /api/price` with query passthrough (`range`, `interval`, `exchange`).
  - Codepaths: `backend/app/api/routes.py`, `backend/app/providers/market_price_provider.py`.
- ASX daily workflow split clarified in runtime:
  - `daily_asx_all_announcements_action.py` for a single explicit day (`--date`).
  - `daily_asx_marketwide_action.py` for lookback windows (`--days`) with optional fallback ticker sweep.
  - Codepaths: `scripts/daily_asx_all_announcements_action.py`, `scripts/daily_asx_marketwide_action.py`.
- Bulk enrichment and coverage workflows added to operations:
  - `scripts/asx_enrichment_sweep_action.py`
  - `scripts/run_asx_enrichment_chunked.py`
  - `scripts/probe_all_system_tickers.py`
- MarketIndex headed-recovery marker taxonomy extended:
  - `blocked_marketindex_no_candidate`
  - `blocked_marketindex_headed_error`
  - Codepaths: `backend/app/services/marketindex_headed_recovery.py`, `backend/app/services/pipeline.py`.
- Cockpit runtime guardrails expanded:
  - heavy-action conflict groups
  - report-based quality gate evaluation
  - codepaths: `cockpit/core/action_runtime_guards.py`, `cockpit/core/job_runner.py`.

Risk notes:
- `daily_asx_marketwide` action id in cockpit currently maps to the single-day all-announcements script (`scripts/daily_asx_all_announcements_action.py`); naming can mislead operators expecting `--days` behavior.
- Enrichment sweep/chunk runs are intentionally strict and can fail fast on guardrails (`max_errors`, quality-gate checks).
- `/api/price` depends on upstream Yahoo chart APIs and can return transient provider failures/rate limits.

## Validation summary
- Compile checks passed for modified Python modules at commit time.
- CLI smoke checks passed where dependencies were available.
- Environment missing-dependency failures were explicitly recorded during validation.
- Documentation references in this file are verified against current codepaths listed above.
