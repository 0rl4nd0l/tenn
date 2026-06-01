# Extraction CTM Source Period Type Correction V1

## Result

Implemented a bounded source-backed period-type correction for CTM-style annual
reports where Pass 1 classifies `H` but the source document has an unambiguous
typed period-end phrase such as `year ended 31 December 2025`.

The correction:

- uses only `_detect_source_period_end_evidence()` output with both
  `period_type` and `period_end`;
- records `source_period_type_correction` in the payload;
- leaves `_validate_gate()` mismatch checks intact for unresolved conflicts;
- does not change prompts, metric extraction values, source PDFs, schema, direct
  datastore writes, Qdrant/news/memory, Cockpit UI, or GitHub state.

## Validation

- `python3 -m py_compile financial-engine_v2/backend/app/services/multipass_extraction.py financial-engine_v2/backend/tests/test_multipass_extraction.py` passed.
- `financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_multipass_extraction.py::test_run_multipass_corrects_period_type_from_explicit_source_period_end -q` passed: `1 passed`.
- `financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_multipass_extraction.py -q` passed: `163 passed`.
- `financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_extraction_pre_canary_truth_gates.py financial-engine_v2/backend/tests/test_extraction_capability_guards.py -q` passed: `22 passed`.
- `financial-engine_v2/.venv/bin/python -m ruff check financial-engine_v2/backend/app/services/multipass_extraction.py financial-engine_v2/backend/tests/test_multipass_extraction.py` passed.
- Post-change code-review pass found no blocking findings.

## Remaining Work

Runtime extraction has not been rerun in this card. Next safe step is a bounded
CTM-only runtime rerun through `POST /api/process/document/{document_id}` after
fresh registry, GPU, backend, worker, source-row, and queue gates pass.

