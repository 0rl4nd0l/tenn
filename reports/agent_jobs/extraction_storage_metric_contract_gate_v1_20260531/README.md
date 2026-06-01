# Extraction Storage Metric Contract Gate V1

## Summary

Implemented a storage-boundary hardening slice for Metric Ontology V1.
`_upsert_financial_rows()` now writes only final extractor-output metrics into
canonical periodic financial rows and fails closed if that whitelist drifts from
`METRIC_FIELDS`.

Persisted-only model columns such as `total_equity` and `interest_expense`
remain present, but extraction payloads no longer populate them until a
separate extractor/evaluator/policy promotion exists.

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

- `financial-engine_v2/backend/app/services/pipeline.py`
- `financial-engine_v2/backend/tests/test_pipeline_stages.py`
- `docs/extraction/metric_extraction_contract.md`
- `docs/claude/STATE.md`
- `docs/agent_tasks/extraction_storage_metric_contract_gate_v1_20260531.md`
- `reports/agent_jobs/extraction_storage_metric_contract_gate_v1_20260531/*`

## Validation

- `py_compile` for touched Python files: passed
- New focused regression: `1 passed`
- Pipeline-stage suite plus upsert source guard: `27 passed`
- Multipass upsert smoke: `1 passed`
- Targeted Ruff: passed

## Remaining Full-Goal Gaps

This does not complete full accurate extraction. Third canary execution,
actual-payload scorecard evidence, source-reviewability/schema-boundary
resolution, and broader accuracy evidence remain required before graduation.
