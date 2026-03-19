# Regression Baselines

This directory stores baseline metrics used by the Regression Guard.

## Purpose
- Prevent silent quality degradation between successful runs.
- Compare current eval metrics against protected baseline metrics.
- Block task completion/PR stage when regressions exceed configured tolerances.

## Files
- `baseline_metrics.json`: canonical baseline payload consumed by `autodev/runtime/regression_guard.py`.

## Baseline update flow
1. Run autodev with successful gates.
2. Set `AUTODEV_ALLOW_BASELINE_INIT=1` to create an initial baseline when missing.
3. Set `AUTODEV_ALLOW_BASELINE_UPDATE=1` to allow baseline refresh only on successful runs.

## Baseline schema
```json
{
  "schema_version": 1,
  "created_at": "2026-03-04T00:00:00Z",
  "source_run_id": "20260304T081134Z",
  "metrics": {}
}
```
