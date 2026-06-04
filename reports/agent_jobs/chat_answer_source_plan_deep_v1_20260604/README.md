# Chat Answer Source Plan Deepening

Generated: 2026-06-04

## Scope

Implemented the second handoff slice: source ordering, canonical numeric truth
eligibility, context-only memory roles, missing-category mapping, and bounded
missing-data recovery expansion now live behind a backend answer-source-plan
interface.

## Changes

- Added `financial-engine_v2/backend/app/services/answer_source_plan.py`.
- Kept `query_orchestrator.build_plan()` as the existing compatibility entry
  point while delegating to the new source-plan module.
- Updated source-role labeling, source-specific missing-category mapping,
  recovery source expansion, and answer-input guidance to consume the module.
- Added focused tests for canonical numeric truth, context-only memory roles,
  deterministic recovery ordering, and missing-category ownership.

## Guardrails

- No DB, Qdrant, memory-store, financial truth data, runtime-service,
  embeddings, extraction, ingestion, schema, or vector changes.
- Company, market, and user thesis memory remain context-only and cannot
  satisfy canonical numeric truth.
- This slice does not include frontend presentation, browser harness, or
  `MultipassResult` contract work.

## Validation

- `financial-engine_v2/backend/tests/test_answer_source_plan.py`
- `financial-engine_v2/backend/tests/test_query_orchestrator.py`
- Focused chat/evidence backend bundle: 135 passed
- Ruff on touched Python files: passed
