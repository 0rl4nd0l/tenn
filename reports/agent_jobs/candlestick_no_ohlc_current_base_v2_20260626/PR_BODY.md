## Summary

Refs #275.

- return a structured `DATA_MISSING` no-data response when `show_candlestick`
  has no backend OHLC history
- include safe no-data chart HTML instead of a raw action-failure 404
- cover the no-OHLC path with a focused backend action-execute regression

## Validation

- `pytest test_cockpit_api_action_execute.py` => 11 passed
- `ruff check` touched Python files => passed
- `py_compile` touched Python files => passed
- `git diff --check` => passed
- task-card validate / overlap / claim => passed

Known caveat: `ruff format --check` still reports broad legacy formatting churn
in the two touched files. It was not applied to avoid unrelated reformatting.

## Safety

- no runtime/service start
- no DB/Qdrant/Redis/news/memory/source-PDF/gold-label/model/service config
  mutation
- no fabricated candles, external market-data fetch, or frontend-only evidence
  relabeling
