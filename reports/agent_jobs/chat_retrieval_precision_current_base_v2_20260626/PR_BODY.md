## Summary

Fixes issue #257 by making `compute_retrieval_precision()` honor explicit
`final_score` values and keep attached-source-only chunks out of primary
retrieval precision.

## Changes

- Treat explicit `final_score: 0.0` as a real score.
- Fall back to `relevance_score` only when `final_score` is missing or invalid.
- Exclude `source_kind` `ephemeral` and `concat` chunks from the primary metric.
- Add focused scorer regressions for the metric contract.

## Validation

- `python -m pytest ... financial-engine_v2/backend/app/services/tests/test_chat_quality_scorer.py -q` - 12 passed
- `ruff check financial-engine_v2/backend/app/services/chat_quality_scorer.py financial-engine_v2/backend/app/services/tests/test_chat_quality_scorer.py` - passed
- `ruff format --check financial-engine_v2/backend/app/services/chat_quality_scorer.py financial-engine_v2/backend/app/services/tests/test_chat_quality_scorer.py` - passed
- `python3 -m py_compile financial-engine_v2/backend/app/services/chat_quality_scorer.py financial-engine_v2/backend/app/services/tests/test_chat_quality_scorer.py` - passed
- `git diff --check` - passed

Notes:

- No live app/API/telemetry process was started; runtime functionality proof
  remains `PARTIAL` pending CI, merge containment, and any operator-level
  runtime smoke that may be desired separately.
