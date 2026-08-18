# Extraction Payload Field Provenance

## Objective

Implement one bounded #286 extraction-only safe extension: add structured
payload-level field provenance for pass4-reconciled metrics.

## Current State

DONE_WITH_RISK pending PR review. A narrow backend code/test change exists and
focused validation passed.

## Why This Slice

Issue #286 remains open after PR #349 because the accounting-number parser child
is fixed, but payloads still lack structured per-field provenance. This slice is
the next highest-value extraction-only class because it makes existing
source-bound `row_refs`, page, table/source, scale, currency, and period evidence
machine-readable without touching persistence/schema, stores, prompts, source
PDFs, gold labels, or broad runtime paths.

## Evidence Used

- Fresh worktree:
  `/home/l4nd0/tenn-payload-field-provenance-v1-20260616`
- Base:
  `origin/migration/clean-runtime-baseline-reconstruct-v1`
  `4b2b9e4c769617e21e94bbc90ec0fc420f170df9`
- Issue #286 live state: open, ready, priority P1.
- Registry read-only: `ok=true`, `read_only=true`, `active_jobs=[]`.
- Code seam:
  `financial-engine_v2/backend/app/services/multipass_extraction.py`
  `_run_pass4_reconciler()` and Appendix wrapper source overlay.

## Files Touched

- `docs/agent_tasks/extraction_payload_field_provenance_v1_20260616.md`
- `financial-engine_v2/backend/app/services/multipass_extraction.py`
- `financial-engine_v2/backend/tests/test_multipass_extraction.py`
- `reports/agent_jobs/extraction_payload_field_provenance_v1_20260616/README.md`
- `reports/agent_jobs/extraction_payload_field_provenance_v1_20260616/status.json`
- `reports/agent_jobs/extraction_payload_field_provenance_v1_20260616/validation.json`
- `reports/agent_jobs/extraction_payload_field_provenance_v1_20260616/diff-check.json`

## Files Intentionally Not Touched

- DB, Qdrant, Redis, news, memory, source PDFs, gold labels, prompts, schema,
  runtime/service/model/GPU config, and production data.
- Full #286 persistence/schema migration.
- Broad extraction/backfill/count-24/count-32 paths.
- LBL companion period binding, except avoiding any change to that path.

## Implementation

- Added `field_provenance` to pass4 payloads.
- Each populated entry includes metric, source/table label, page number/tag,
  row reference/excerpt, scale, scale source, currency, period type, and period
  end.
- Optional `source_document_id` or `extraction_run_id` is included only if an
  upstream payload already provides it; this slice does not invent identifiers.
- Existing `provenance`, `row_refs`, `metric_source_scales`, and
  `metric_scale_sources` behavior is preserved.
- Appendix wrapper source overlays now update `field_provenance` when they
  overwrite wrapper-owned metrics.

## Commands Run

- `git fetch origin --prune`: exit 0.
- `python3 scripts/agent_job_registry.py list-active --read-only`: exit 0.
- `gh issue view 286 --json number,title,state,labels,updatedAt,url,body`: exit 0.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_payload_field_provenance_v1_20260616.md`: exit 0.
- RED:
  `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with pytest python -m pytest -c pytest.ini financial-engine_v2/backend/tests/test_multipass_extraction.py::test_pass4_emits_structured_field_provenance_for_metrics -q`: exit 1, failed with `KeyError: 'field_provenance'`.
- GREEN:
  `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with pytest python -m pytest -c pytest.ini financial-engine_v2/backend/tests/test_multipass_extraction.py::test_pass4_emits_structured_field_provenance_for_metrics financial-engine_v2/backend/tests/test_multipass_extraction.py::test_pass4_common_metric_source_scale_overrides_document_scale financial-engine_v2/backend/tests/test_multipass_extraction.py::test_pass3a_parses_common_accounting_number_strings -q`: exit 0, 3 passed.
- Wrapper guardrails:
  `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with pytest python -m pytest -c pytest.ini financial-engine_v2/backend/tests/test_multipass_extraction.py::test_pass4_emits_structured_field_provenance_for_metrics financial-engine_v2/backend/tests/test_multipass_extraction.py::test_run_multipass_carries_gpt_appendix_4d_source_bound_payload financial-engine_v2/backend/tests/test_multipass_extraction.py::test_run_multipass_uses_explicit_source_text_scale_when_tables_missing financial-engine_v2/backend/tests/test_multipass_extraction.py::test_run_multipass_appendix_4d_fails_closed_without_wrapper_disclosures -q`: exit 0, 4 passed.
- `python3 -m py_compile financial-engine_v2/backend/app/services/multipass_extraction.py`: exit 0.
- `uv run --with ruff ruff check financial-engine_v2/backend/app/services/multipass_extraction.py financial-engine_v2/backend/tests/test_multipass_extraction.py`: exit 0.
- `python3 -m json.tool reports/agent_jobs/extraction_payload_field_provenance_v1_20260616/status.json >/dev/null && python3 -m json.tool reports/agent_jobs/extraction_payload_field_provenance_v1_20260616/validation.json >/dev/null`: exit 0.
- `git diff --check`: exit 0.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_payload_field_provenance_v1_20260616.md --repo-root .`: exit 0.

## Validation Status

Focused validation passed. No broad extraction, samples, backfills, service
routes, or production mutations were run.

## DATA_MISSING

- No persistence/schema migration is included in this slice.
- No broad accuracy or runtime coverage claim is made.
- `extraction_run_id` and `source_document_id` remain absent unless upstream
  extraction metadata already provides them to pass4.

## Remaining Risk

This repairs payload-level structured provenance for extracted metrics. It does
not persist per-field provenance into a new database table or prove corpus-wide
accuracy.

## Next Recommended Prompt

Review and merge the narrow #286 child PR for payload-level field provenance;
then decide whether the next #286 slice should wire this structured payload into
persistence or tighten source excerpt/page display in review tooling.
