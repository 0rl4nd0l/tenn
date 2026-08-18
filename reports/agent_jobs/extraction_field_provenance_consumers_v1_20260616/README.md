# Extraction Field Provenance Consumers

## Objective

Implement one bounded #286 extraction-only safe extension: make existing
payload consumers prefer structured `field_provenance` while preserving legacy
`provenance` fallback.

## Current State

DONE_WITH_RISK pending PR review. A narrow backend code/test change exists and
focused validation passed.

## Why This Slice

Issue #286 remains open after PR #350 because the extraction payload now carries
structured field provenance, but review/evaluation/provenance consumers still
primarily read legacy string `provenance`. This slice is the next highest-value
extraction-only step because it makes the new structured payload useful without
touching persistence/schema, stores, prompts, source PDFs, gold labels, runtime,
or broad extraction paths.

## Evidence Used

- Fresh worktree:
  `/home/l4nd0/tenn-field-provenance-consumers-v1-20260616`
- Base:
  `origin/migration/clean-runtime-baseline-reconstruct-v1`
  `227e1ce0d4e99c4a13ece8012a44adeba4585cdf`
- Issue #286 live state: open, ready, priority P1.
- Registry read-only: `ok=true`, `read_only=true`, `active_jobs=[]`.
- Consumer seams:
  `financial-engine_v2/backend/app/services/provenance.py`,
  `financial-engine_v2/backend/app/services/extraction_eval.py`, and
  `financial-engine_v2/backend/app/services/extraction_review.py`.

## Files Touched

- `docs/agent_tasks/extraction_field_provenance_consumers_v1_20260616.md`
- `financial-engine_v2/backend/app/services/provenance.py`
- `financial-engine_v2/backend/app/services/extraction_eval.py`
- `financial-engine_v2/backend/app/services/extraction_review.py`
- `financial-engine_v2/backend/tests/test_provenance_adapter.py`
- `financial-engine_v2/backend/tests/test_extraction_eval.py`
- `financial-engine_v2/backend/tests/test_extraction_review_service.py`
- `reports/agent_jobs/extraction_field_provenance_consumers_v1_20260616/README.md`
- `reports/agent_jobs/extraction_field_provenance_consumers_v1_20260616/status.json`
- `reports/agent_jobs/extraction_field_provenance_consumers_v1_20260616/validation.json`
- `reports/agent_jobs/extraction_field_provenance_consumers_v1_20260616/diff-check.json`

## Files Intentionally Not Touched

- DB, Qdrant, Redis, news, memory, source PDFs, gold labels, prompts, schema,
  runtime/service/model/GPU config, and production data.
- Full #286 persistence/schema migration.
- Broad extraction/backfill/count-24/count-32 paths.

## Implementation

- Added `from_extraction_payload_metric()` to consume one metric from structured
  `field_provenance`, falling back to legacy string `provenance`.
- Updated `from_extraction_payload()` to prefer structured field provenance and
  still include legacy-only metrics if a payload is mixed.
- Updated extraction evaluation provenance summaries to treat
  `field_provenance` as available evidence.
- Updated extraction review items to use the shared payload metric adapter, so
  page/table/evidence fields work without legacy `provenance`.

## Commands Run

- `git fetch origin --prune`: exit 0.
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`: exit 0.
- `gh issue view 286 --json number,title,state,labels,updatedAt,url,body`: exit 0.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_field_provenance_consumers_v1_20260616.md`: exit 0.
- RED:
  `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with pytest python -m pytest -c pytest.ini financial-engine_v2/backend/tests/test_provenance_adapter.py::test_from_extraction_payload_prefers_structured_field_provenance financial-engine_v2/backend/tests/test_extraction_review_service.py::test_build_review_item_uses_structured_field_provenance -q`: exit 1, failed because adapter returned zero records and review page number was `None`.
- GREEN:
  `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with pytest python -m pytest -c pytest.ini financial-engine_v2/backend/tests/test_provenance_adapter.py::test_from_extraction_payload_prefers_structured_field_provenance financial-engine_v2/backend/tests/test_provenance_adapter.py::test_from_extraction_payload_normalizes_metric_collection financial-engine_v2/backend/tests/test_extraction_eval.py::test_evaluate_fixture_uses_structured_field_provenance_summary financial-engine_v2/backend/tests/test_extraction_review_service.py::test_build_review_item_uses_structured_field_provenance financial-engine_v2/backend/tests/test_extraction_review_service.py::test_build_review_item_includes_provenance_and_snippet -q`: exit 0, 5 passed.
- `python3 -m py_compile financial-engine_v2/backend/app/services/provenance.py financial-engine_v2/backend/app/services/extraction_eval.py financial-engine_v2/backend/app/services/extraction_review.py`: exit 0.
- `uv run --with ruff ruff check financial-engine_v2/backend/app/services/provenance.py financial-engine_v2/backend/app/services/extraction_eval.py financial-engine_v2/backend/app/services/extraction_review.py financial-engine_v2/backend/tests/test_provenance_adapter.py financial-engine_v2/backend/tests/test_extraction_eval.py financial-engine_v2/backend/tests/test_extraction_review_service.py`: exit 0.
- `python3 -m json.tool reports/agent_jobs/extraction_field_provenance_consumers_v1_20260616/status.json >/dev/null && python3 -m json.tool reports/agent_jobs/extraction_field_provenance_consumers_v1_20260616/validation.json >/dev/null`: exit 0.
- `git diff --check`: exit 0.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_field_provenance_consumers_v1_20260616.md --repo-root .`: exit 0.

## Validation Status

Focused validation passed. No broad extraction, samples, backfills, service
routes, or production mutations were run.

## DATA_MISSING

- No persistence/schema migration is included in this slice.
- No broad accuracy or runtime coverage claim is made.

## Remaining Risk

This wires structured payload provenance into existing consumers. It does not
persist per-field provenance into a new database table or prove corpus-wide
accuracy.

## Next Recommended Prompt

Review and merge the narrow #286 consumer PR; then decide whether the next #286
slice should persist `field_provenance` or close/update #286 with the completed
parser, payload, and consumer children.
