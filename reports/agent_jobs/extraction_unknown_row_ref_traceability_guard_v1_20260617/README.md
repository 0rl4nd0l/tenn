# Unknown Row-Ref Traceability Guard

State: VALIDATING
Mode: SAFE_EXTENSION_CONSUMER_TRACEABILITY_GUARD

## Objective

Implement the narrow issue #286 guard approved by the operator: structured
`field_provenance` entries whose `row_ref` or `excerpt` is `unknown` must not be
reported as precise provenance solely because they have a page tag.

## Behavior Changed

`financial-engine_v2/backend/app/services/provenance.py` now downgrades such
structured entries to `low_traceability`. Real structured field provenance with
actual row evidence remains `precise`. Derived and prose-note behavior was not
changed.

## Files Changed

- `docs/agent_tasks/extraction_unknown_row_ref_traceability_guard_v1_20260617.md`
- `financial-engine_v2/backend/app/services/provenance.py`
- `financial-engine_v2/backend/tests/test_provenance_adapter.py`
- `reports/agent_jobs/extraction_unknown_row_ref_traceability_guard_v1_20260617/`

## Validation

- RED focused pytest: failed as expected because current behavior returned
  `precise` for unknown structured row evidence.
- GREEN focused pytest: `2 passed`.
- Full provenance adapter suite: `14 passed`.
- `python3 -m py_compile` on touched Python files: passed.
- Ruff on touched Python/test files: passed.

Final diff-contract checks are recorded in `validation.json` after staging.

## What This Proves

- Unknown structured row evidence is now surfaced as low traceability.
- Existing precise structured field provenance remains precise.
- This is a consumer traceability fix only.

## What This Does Not Prove

- It does not prove extraction values are correct.
- It does not run count-24, count-32, broad extraction, or backfill.
- It does not mutate canonical rows, DB, Qdrant, Redis, news, memory, source
  PDFs, prompts, gold labels, schema, runtime, service, model, or GPU state.

## Next Recommended Step

Prepare this branch for review, then use the result for owner-approved issue
#286 closeout wording or PR prep. Do not move to count-32 until the owner accepts
this provenance-honesty guard and the remaining saved-artifact evidence.
