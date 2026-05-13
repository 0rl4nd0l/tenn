# Diff Risk Assessment

## High-level summary
The dirty diff is additive and focused on runtime provenance and reportability of the real-gold extraction pipeline.

## File-level risk

| File | Highest risk class | Why it matters | Failure mode if wrong |
|---|---|---|---|
| financial-engine_v2/backend/app/main.py | production-path API contract | Adds response timing and provenance fields to eval output. | Consumer-facing schema drift if callers expect exact keys; low if additive but must validate downstream consumers/tests. |
| financial-engine_v2/backend/app/services/docling_extract.py | production-path extraction | Adds metadata fields to `StructuredDocument` and cache serialisation. | Corruption if cache shape is misread during fallback/reload (mitigated by defaults). |
| financial-engine_v2/backend/app/services/method_isolated_extraction.py | production-path extraction | Adds metadata to method provenance map. | Low; missing field handling fallback defaults are null-safe. |
| financial-engine_v2/backend/app/services/multipass_extraction.py | production-path extraction | Carries metadata into extraction result summary. | Low; additive. |
| financial-engine_v2/backend/tests/test_docling_extract.py | test coverage | Validates new metadata semantics for cached/extracted paths. | Low; false confidence if expectations are too narrow. |
| financial-engine_v2/backend/tests/test_extraction_gold_eval.py | test coverage | Validates null and non-null runtime fields in eval endpoint payload. | Low; no production impact. |
| scripts/run_real_extraction_eval.py | eval tooling | Adds fields to report rows/rollups. | Low; export schema change in downstream spreadsheet consumers. |
| scripts/test_run_real_extraction_eval.py | test coverage | Asserts rollup/export includes runtime columns. | Low; lock to current filename/column-order assumptions. |

## Safety bucket classification
- No high-risk truth-path logic changes.
- No financial metric canonicality logic changes.
- No routing/API orchestration changes.
- No tests for runtime services were executed (audit-only).

## Highest-risk files
- `financial-engine_v2/backend/app/main.py`
- `financial-engine_v2/backend/app/services/docling_extract.py`

## Recommended mitigation before integration
- Replay these changes on current preserve head and run at least the touched eval tests before merge.
- Confirm cache backward compatibility for existing `.docling.json` artifacts (fields are optional and should remain safe).
