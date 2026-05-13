# Dirty File Matrix

## Files and classifications

| File | State | Lane | Purpose | Root-cause category | Safety category | Risk if lost | Risk if committed | Prescribe decision |
|---|---|---|---|---|---|---|---|---|
| financial-engine_v2/backend/app/main.py | modified | Evaluation | Eval API response enrichment (`_evaluate_real_gold_document`) | eval reporting | production-path code | medium | medium | preserve_now_in_new_branch_or_commit |
| financial-engine_v2/backend/app/services/docling_extract.py | modified | Evaluation | extraction/runtime metadata (`timeout_budget_sec`, cache flags) | extraction scoring | production-path code | medium | medium | preserve_now_in_new_branch_or_commit |
| financial-engine_v2/backend/app/services/method_isolated_extraction.py | modified | Evaluation | Method provenance enrichment | instrumentation | production-path code | low | low | preserve_now_in_new_branch_or_commit |
| financial-engine_v2/backend/app/services/multipass_extraction.py | modified | Evaluation | Multipass provenance enrichment | instrumentation | production-path code | low | low | preserve_now_in_new_branch_or_commit |
| financial-engine_v2/backend/tests/test_docling_extract.py | modified | Evaluation | Docling extraction cache/runtime behavior tests | test coverage | safe docs/report only | medium | low | preserve_now_in_new_branch_or_commit |
| financial-engine_v2/backend/tests/test_extraction_gold_eval.py | modified | Evaluation | Real-gold eval response regression tests | eval reporting | safe docs/report only | high | low | preserve_now_in_new_branch_or_commit |
| scripts/run_real_extraction_eval.py | modified | Evaluation | Eval rollup/CSV export instrumentation fields | eval reporting | eval-only code | medium | low | preserve_now_in_new_branch_or_commit |
| scripts/test_run_real_extraction_eval.py | modified | Evaluation | Script-level artifact tests | test coverage | safe docs/report only | medium | low | preserve_now_in_new_branch_or_commit |

## Surface touch notes
- Touches extraction truth indirectly through runtime metadata propagation: `docling_extract.py`, `method_isolated_extraction.py`, `multipass_extraction.py`.
- Touches eval reporting directly: `main.py`, `run_real_extraction_eval.py`, `test_extraction_gold_eval.py`.
- Does not touch routing, API auth, storage schema, or runtime data stores.
