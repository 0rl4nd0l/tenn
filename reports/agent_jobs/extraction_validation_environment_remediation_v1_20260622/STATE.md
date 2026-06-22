# State

## Current Branch

- Worktree: `/home/l4nd0/tenn-extraction-metric-improvement-sprint-v1-20260622`
- Branch: `safe/extraction-metric-improvement-sprint-v1-20260622`
- Base PR: draft PR #384
- Remediation task card: `docs/agent_tasks/extraction_validation_environment_remediation_v1_20260622.md`

## Root Cause

The prior sprint had two validation-control-plane gaps:

1. Focused pytest depended on an approved replay venv that had extraction
   runtime dependencies but did not have pytest installed. The attempted ad hoc
   fallback did not reuse that venv's site-packages and began pulling an
   unsuitable dependency stack.
2. Full certified no-write replays could hang inside local Docling or LLM calls
   without producing terminal replay artifacts.

## Implemented State

- Added `scripts/run_pytest_with_fallback.py`.
- Added `scripts/test_run_pytest_with_fallback.py`.
- Added `--case-timeout-seconds` to `scripts/extraction_no_write_replay.py`.
- Classified case timeout rows as infrastructure failures so aggregate replay
  status becomes `DATA_MISSING`.
- Updated `docs/validation_baseline.md` with the required helper command and
  timeout semantics.

## Git / Ledger / Registry

- Live task ledger: `DATA_MISSING`.
- Committed task ledger: available, no matches for this exact remediation.
- Fallback search: no active duplicate implementation found.
- Registry: task claimed under
  `extraction_validation_environment_remediation_v1_20260622`.

## Docs Impact

- docs_impact: `DOCS_UPDATED`
- docs_checked:
  - `docs/validation_baseline.md`
  - `scripts/extraction_no_write_replay.py`
  - `scripts/run_pytest_with_fallback.py`
- docs_changed:
  - `docs/validation_baseline.md`
- docs_followup: `NONE`

## Model / Worker Routing

- task_tier: `large`
- recommended_model: `high reasoning`
- actual_model: `Codex GPT-5`
- worker_model_allowed: `false`
- escalation_needed: `false`
