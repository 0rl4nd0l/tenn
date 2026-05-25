# Diff Review

## Scope

Reviewed changed files:

- `financial-engine_v2/backend/app/services/chat_evidence_guard.py`
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/backend/tests/test_chat_evidence_guard.py`
- `financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py`
- `financial-engine_v2/backend/tests/test_sources.py`

## Findings

### Fixed During Review

- Streaming local-news-only responses initially applied the guard only to the
  final `done` event. That could still leak unguarded model chunks before the
  corrected final answer. Fixed by exposing `requires_local_news_only_guard()`
  and suppressing incremental SSE chunks for local-news-only requests, with
  final guarded text still delivered in the `done` event.

- The broader source-label validation suite exposed fixture drift in
  `test_sources.py`: current Cockpit source normalization adds
  `financial_truth_numeric` to non-claim-verified financial-truth sources. The
  fixture now expects both `financial_truth` and `financial_truth_numeric`,
  preserving the honest distinction between numeric context and
  claim-verified evidence.

### Remaining Findings

No critical findings, warnings, or suggestions remain from the final scoped
review.

## Checklist

- Clarity/readability: pass.
- Naming: pass.
- Duplication: pass. The guard reuses existing label/source helper patterns.
- Error handling: pass. The guard is deterministic and does not perform I/O.
- Secrets/API keys: pass. No secrets added.
- Input validation: pass. User message and source fields are normalized via
  string helpers before classification.
- Test coverage: pass. Unit and route tests cover A2M canary, non-A2M local
  news, no-local-news control, context-only evidence, claim-verified evidence,
  degraded runtime preservation, and streaming chunk suppression.
- Performance: pass. The guard scans visible source lists only.

## Architecture Review

- No DB writes.
- No Qdrant writes.
- No news-store writes.
- No reindex, resync, backfill, or projection repair.
- No parser routing changes.
- No canonical financial-truth writes.
- No Tenn memory writes.
- No runtime/model/GPU config changes.
- No UI redesign.
- No A2M-specific alias hardcoding.

## Validation Evidence

See `validation_results.json` for command-level validation details.
