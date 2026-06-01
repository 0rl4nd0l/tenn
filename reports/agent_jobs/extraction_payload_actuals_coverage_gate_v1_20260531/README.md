# Extraction Payload Actuals Coverage Gate V1

## Summary

Implemented a report-local payload actuals coverage gate for confirmed-metric
scorecards. The scorecard now reports actual payload ids that match the fixture
scope and actual payload ids that do not. The pre-persistence gate fails when
unmatched actual payload documents are present.

This prevents a canary/review artifact from silently ignoring supplied
extraction outputs that were outside the scorecard fixture set.

## Boundaries

- Runtime canary executed: false
- Broad backfill executed: false
- Production data access: false
- DB/Qdrant/news/memory mutation: false
- Source PDF mutation: false
- Parser/prompt/schema migration: false
- Runtime/model/GPU/service mutation: false
- Cockpit UI/GitHub mutation: false

## Files Changed

- `financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py`
- `financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py`
- `scripts/test_extraction_gold_eval_scorecard.py`
- `docs/extraction/metric_extraction_contract.md`
- `docs/claude/STATE.md`
- `docs/agent_tasks/extraction_payload_actuals_coverage_gate_v1_20260531.md`
- `reports/agent_jobs/extraction_payload_actuals_coverage_gate_v1_20260531/*`

## Validation

- `py_compile` for touched Python files: passed
- Focused unmatched-actuals backend regression: `1 passed`
- Script unmatched-actuals regression: passed via script suite
- Full scorecard service tests: `32 passed`
- Script tests: `5 passed`
- Targeted Ruff: passed
- `git diff --check`: passed

## Remaining Full-Goal Gaps

This strengthens actual-payload reviewability but does not complete full
accurate extraction. Runtime canary execution, current actual payload evidence
from approved runs, source-reviewability/schema-boundary resolution, and
broader accuracy evidence remain required before graduation.
