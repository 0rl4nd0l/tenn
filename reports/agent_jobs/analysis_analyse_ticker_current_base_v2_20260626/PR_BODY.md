## Summary

Fixes issue #253 by making `analyse_ticker()` instantiate
`TickerContextLoader` before calling `load()`.

## Changes

- Import the existing analysis RAG adapter for the high-level helper.
- Construct `TickerContextLoader(rag_fn=analysis_rag_query)`.
- Call the instance `loader.load(...)` with the merged context request.
- Add a focused regression proving the loader is instantiated and the
  orchestrator receives the loaded context.

## Validation

- `python -m pytest ... financial-engine_v2/backend/tests/test_analysis_modules.py -q` - 49 passed
- `ruff check financial-engine_v2/backend/app/modules/orchestrator.py financial-engine_v2/backend/tests/test_analysis_modules.py` - passed
- `python3 -m py_compile financial-engine_v2/backend/app/modules/orchestrator.py financial-engine_v2/backend/tests/test_analysis_modules.py` - passed
- `git diff --check` - passed

Notes:

- `ruff format --check` would reformat both touched files because canonical has
  pre-existing whole-file format drift. I reverted formatter churn and kept the
  minimal source/test diff.
- No live app/API process was started; runtime functionality proof remains
  `PARTIAL` pending CI, merge containment, and any operator-level runtime smoke
  that may be desired separately.
