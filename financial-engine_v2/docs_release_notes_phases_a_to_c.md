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

## Validation summary
- Compile checks passed for modified Python modules at commit time.
- CLI smoke checks passed where dependencies were available.
- Environment missing-dependency failures were explicitly recorded during validation.
