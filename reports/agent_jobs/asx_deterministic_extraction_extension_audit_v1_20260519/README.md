# ASX Deterministic Extraction Extension Audit v1

Job: `asx_deterministic_extraction_extension_audit_v1_20260519`

Mode: `AUDIT ONLY`

## 1. Executive Verdict

- Verdict: `ASX_DETERMINISTIC_EXTENSION_READY_FOR_DESIGN`
- Canonical truth status: `CANONICAL_TRUTH_SAFE`
- Recommended next task: create an ASX document-type fixture/schema contract task first, then a pure classifier unit-test task. Do not start with parser routing.

Rationale: Tenn already has a controlled strict Docling baseline, real-gold trust semantics, confirmed metric coverage reporting, and deterministic table-location logic that can host sidecar comparison. The safe extension route is comparator-first and fixture-first. The unsafe route is changing parser routing, prompts, gold labels, or persistence before no-regression gates prove behavior.

## 2. Confirmed Facts

Files and reports inspected:
- `docs/architecture/05_pdf_extraction_and_chunking.md`
- `docs/architecture/12_evaluation_and_drift_monitoring.md`
- `docs/architecture/SYSTEM_CONTRACT.md`
- `docs/extraction/metric_extraction_contract.md`
- `financial-engine_v2/backend/app/main.py`
- `financial-engine_v2/backend/app/services/docling_extract.py`
- `financial-engine_v2/backend/app/services/method_isolated_extraction.py`
- `financial-engine_v2/backend/app/services/multipass_extraction.py`
- `financial-engine_v2/backend/app/services/pipeline.py`
- `financial-engine_v2/backend/app/services/extraction_eval.py`
- `financial-engine_v2/backend/app/services/extraction_gold_eval.py`
- `financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py`
- `financial-engine_v2/backend/app/services/confirmed_metric_coverage_review.py`
- `financial-engine_v2/backend/app/services/validation/extraction_schemas.py`
- `financial-engine_v2/data/extraction_gold_real/README.md`
- `financial-engine_v2/backend/tests/test_docling_extract.py`
- `financial-engine_v2/backend/tests/test_multipass_extraction.py`
- `financial-engine_v2/backend/tests/test_extraction_gold_eval.py`
- `financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py`
- `financial-engine_v2/backend/tests/test_confirmed_metric_coverage_api.py`
- `financial-engine_v2/backend/tests/test_confirmed_metric_coverage_review.py`
- `financial-engine_v2/backend/tests/test_extraction_capability_guards.py`
- `scripts/document_classifier.py`
- `scripts/extract_financial_metrics.py`
- `scripts/cashflow_table_fallback.py`
- `scripts/cashflow_layout_adapter.py`
- `reports/agent_jobs/appendix5b_fifth_doc_approval_packet_v1_20260517/README.md`
- `reports/agent_jobs/appendix5b_fifth_doc_approval_packet_v1_20260517/approval_packet.json`
- `reports/agent_jobs/appendix5b_fifth_doc_approval_packet_v1_20260517/candidate_inventory.json`

Current parser/evaluator owners:
- Parser method selection: `method_isolated_extraction.normalize_extraction_method()` and `run_method_isolated_extraction()`.
- Structured PDF parsing: `docling_extract.extract_structured()` and `StructuredDocument`.
- Multipass extraction/table selection/metric extraction: `multipass_extraction.run_multipass_extraction()`, `_run_pass1_classifier()`, `_run_pass2_locator()`, `_run_pass3a_metric_extractor()`, and Pass 4 reconciliation.
- Production persistence/canonical financial rows: `pipeline._upsert_financial_rows()` and the persistence block that writes `ExtractionRun` plus `ASXPeriodicFinancial` rows.
- Real-gold evaluation: `extraction_gold_eval.evaluate_real_gold_fixture()` and main API real-gold handlers.
- Confirmed metric coverage: `extraction_gold_eval_scorecard.build_confirmed_metric_coverage_scorecard()` and `confirmed_metric_coverage_review.run_confirmed_metric_coverage_review()`.
- Schema reference: `validation/extraction_schemas.py`, currently documented as not activated in the live pipeline.

Existing no-regression gates:
- `canonical_core`: 10 documents / 24 checks.
- `expanded_required`: 15 documents / 39 checks.
- `confirmed_metric_coverage`: API tests assert 15 fixtures / 146 expectations, 73 scored, 70 candidate-review, 3 ambiguous, 0 unsupported.
- Strict Docling tests assert strict Docling does not fallback to PyMuPDF.
- Multipass tests cover Appendix 5B disqualification from income/balance slots, Appendix 5B scale/table merging behavior, quarterly validation accepting limited cashflow metrics, Appendix 4D/4E unit-row detection, net-debt explicit-row guards, share-capital selection, and currency/scale abstain behavior.

Existing Appendix 5B work:
- Current branch has embedded Appendix 5B logic in `multipass_extraction.py`.
- Current branch has tests for Appendix 5B scale, table merging, cashflow-only behavior, and quarterly validation.
- Current branch has `appendix5b_fifth_doc_approval_packet_v1_20260517`, which selected PRM December 2025 as clean manual evidence for `operating_cash_flow = -246000` but did not add it to the no-regression floor because the active branch lacked the standalone Appendix 5B scorer/gate stack.
- No standalone Appendix 5B backend parser/scorer/gate stack was found in this branch.

Existing schema/metric support:
- Multipass extraction emits current schema metrics: `revenue`, `ebit`, `np_attributable`, `operating_cf`, `investing_cf`, `financing_cf`, `capex`, `cash_end`, `net_debt`, and `shares_outstanding`.
- Pipeline persistence also includes `total_equity` and `interest_expense` fields, but those are not the confirmed coverage expansion target here.
- Real-gold API support remains narrower: `revenue`, `operating_cash_flow`, and `net_debt`.
- EPS, EBITDA, NTA, dividends, and total debt are not first-class confirmed metric coverage fields in the inspected scorer mapping.

Existing comparator references:
- `scripts/compare_docling_accuracy.py` exists as a comparison script, but it was not run.
- Camelot exists only as script-level cashflow fallback and is guarded out of backend dependencies.
- No MinerU, Chandra, TATR/Table Transformer, pdfplumber, or pypdfium2 comparator implementation was found in the inspected surfaces.

## 3. Inferred Facts

Safest extension points:
- A deterministic ASX document-type classifier should fit as a read-only sidecar after `StructuredDocument` exists or as a pre-routing report artifact over first-page/title/table-caption evidence.
- It should not initially change `parser_backend`, `strict_parser`, Pass 1 confidence gates, Pass 2 table winners, metric prompts, or persistence.
- Appendix 5B/4C/4D/4E deterministic parsers should first emit comparator artifacts with `canonical_write=false`.
- Annual/half-year statement-table selection can be layered around the existing Pass 2 table locator only after fixture-level tests prove it does not alter canonical_core or expanded_required behavior.

Likely missing tests:
- Dedicated ASX form classifier fixtures for annual report, half-year report, Appendix 4C, Appendix 4D, Appendix 4E, Appendix 5B, and other ASX announcement.
- Appendix 4C cashflow-only parser tests.
- Appendix 4D/4E summary-table conflict tests.
- Comparator artifact schema validation tests.
- Tests that prove classifier artifacts do not affect parser routing or canonical writes.

Likely blast radius if parser routing changes too soon:
- Strict Docling no-regression could be bypassed.
- Pass 1 A/H/Q confidence behavior could be weakened.
- Appendix 5B expected-null income-statement behavior could be violated by receipts/revenue confusion.
- Comparator output could be mistaken for canonical truth.
- Pipeline `_upsert_financial_rows()` could persist unproven values.

## 4. Speculative Claims

- A pure ASX document-type classifier is likely low risk if it is not imported by production routing.
- Appendix 5B and 4C can likely share a line-item cashflow artifact schema.
- Appendix 4D and 4E can likely share summary-table parser structure, with period-type-specific anchors.

These are design hypotheses, not implementation conclusions.

## 5. DATA_MISSING

See `DATA_MISSING.md` for the detailed list. Main gaps:
- Recent broader Gold Metric Coverage Audit report artifacts were not committed in this isolated branch and were not inspected from an active registry-owned runtime path.
- No backend `ASXDocumentType` enum/classifier was found.
- No standalone Appendix 5B backend scorer/gate stack was present in this branch.
- No deterministic Appendix 4C/4D/4E parser modules were found.
- No MinerU/Chandra/TATR/pdfplumber comparator implementation was found.
- Current docs have fixture-count drift: one architecture doc describes 13 fixtures while current fixture directories contain 15 JSON files.

## 6. Extension Point Inventory

Detailed inventory is in `extension_point_inventory.json`.

Summary:
- `method_isolated_extraction.py`: audit/comparator-only safe; routing changes are high risk.
- `docling_extract.py`: safe read-only input surface; fallback semantics are high risk.
- `multipass_extraction.py` Pass 1: high risk to replace; safe to compare against.
- `multipass_extraction.py` Pass 2: medium risk as selector/comparator; high risk if selected table winners drive metrics before gates.
- `multipass_extraction.py` Appendix 5B logic: good current anchor for sidecar parser design; no canonical writes.
- `extraction_gold_eval*.py`: safe read-only measurement surface; gold/trust edits blocked.
- `pipeline.py`: persistence is explicitly blocked for this audit.
- `scripts/document_classifier.py`: broad prior art only, not ASX type truth.
- Camelot scripts: comparator/script-only, not backend dependency or truth.

## 7. ASX Document-Type Classifier Plan

Detailed plan is in `document_type_classifier_plan.json`.

Required document types:
- `annual_report`
- `half_year_report`
- `appendix_4c`
- `appendix_4d`
- `appendix_4e`
- `appendix_5b`
- `other_asx_announcement`

Core policy:
- Every type requires source/title/first-page/table evidence.
- Every type has abstain conditions.
- Classifier output is metadata, not metric truth.
- The classifier must preserve `canonical_write=false` until later promotion gates pass.

## 8. Deterministic Parser Plan

Detailed plan is in `deterministic_parser_plan.md`.

Parser candidates:
- Appendix 5B line-item parser.
- Appendix 4C cashflow line-item parser.
- Appendix 4D/4E summary-table parser.
- Annual/half-year statement table selector.

Common requirements:
- Source anchors.
- Metric candidates limited to schema-supported fields.
- Page/table/row/column binding.
- Trust/abstain rules.
- Sidecar artifact shape.
- Focused tests before any live routing discussion.

## 9. Comparator Artifact Plan

Detailed plan is in `comparator_artifact_plan.md`.

Comparator targets:
- MinerU: no implementation found; external candidate only.
- Chandra: no implementation found; external candidate only.
- Marker: no relevant implementation found; generic Markdown is insufficient truth.
- TATR/Table Transformer: no implementation found; table detection only unless value binding exists.
- pdfplumber/Camelot/pypdfium2: Camelot is script-only; pdfplumber absent; pypdfium2 only appears in a fixture limitation note.

None should write canonical truth.

## 10. No-Regression and Promotion Gates

Detailed gate map is in `no_regression_gate_map.json`.

Promotion requires:
- Canonical10 preservation.
- Expanded required preservation.
- Confirmed metric coverage measurement only from source-evidenced, schema-supported expectations.
- Evidence binding to document, period, currency, scale, table/page/row/column.
- Existing trusted/abstain/quarantine semantics unchanged.
- Runtime provenance for parser id, extractor version, prompt hash where applicable, and source checksums.
- Local feasibility without adding heavy backend parser dependencies or requiring OCR/GPU/runtime mutations.
- No canonical write until every gate passes.

## 11. Safe Roadmap

Smallest safe next tasks:

1. ASX document-type fixture/schema contract only.
   - Suggested allowed files:
     - `docs/agent_tasks/asx_document_type_fixture_contract_v1_20260520.md`
     - `financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/`
     - `reports/agent_jobs/asx_document_type_fixture_contract_v1_20260520/`
   - No source module, no routing, no extraction jobs.

2. Pure classifier module plus unit tests.
   - Suggested allowed files:
     - `financial-engine_v2/backend/app/services/asx_document_type_classifier.py`
     - `financial-engine_v2/backend/tests/test_asx_document_type_classifier.py`
     - fixture files from step 1
     - task/report artifacts
   - Must not be imported by production extraction routing.

3. Read-only comparator artifact schema.
   - Suggested allowed files:
     - `financial-engine_v2/backend/app/services/asx_parser_comparator_artifacts.py`
     - `financial-engine_v2/backend/tests/test_asx_parser_comparator_artifacts.py`
     - task/report artifacts
   - Must emit `canonical_write=false`.

4. Deterministic parser prototypes.
   - Start with Appendix 5B or 4C sidecar parser tests.
   - Do not connect to `_upsert_financial_rows()`.

5. Gate run/report task.
   - Only after sidecar artifacts and fixtures exist.
   - Must compare canonical_core, expanded_required, and confirmed_metric_coverage without changing gold labels.

## 12. Do-Not-Do

Explicitly blocked:
- Replacing Docling.
- Promoting PyMuPDF.
- Treating generic Markdown as truth.
- Treating cloud parser output as production truth.
- Writing comparator output into canonical truth.
- Using shared `:8001` strict extraction/eval comparator work.
- Broad parser routing changes.
- Prompt changes.
- Gold-label changes.
- Canonical writes.
- DB/Qdrant/memory/news/Cockpit/runtime/model/GPU changes.

## 13. Validation Commands Run

Preflight and task-card commands:
- `pwd`: `/home/l4nd0/tenn-asx-deterministic-extraction-audit-v1-20260519`
- `readlink -f /home/l4nd0/tenn-runtime`: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- `git branch --show-current`: `audit/asx-deterministic-extraction-extension-v1-20260519`
- `git rev-parse --short=12 HEAD`: `0b8c4d942be5`
- `git status --short`: task card/report dirt only in the isolated worktree; runtime checkout had unrelated pre-existing untracked task cards before isolation.
- `git worktree list`: confirmed isolated audit worktree and runtime worktree are separate.
- `git show --stat --oneline --no-renames HEAD`: `0b8c4d94 fix(query): allow cockpit control prompts without source refusal`.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/asx_deterministic_extraction_extension_audit_v1_20260519.md`: PASS.
- `python3 scripts/agent_job_registry.py list-active`: PASS; one unrelated active Evaluation job was visible before claim.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/asx_deterministic_extraction_extension_audit_v1_20260519.md`: PASS, no overlap.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/asx_deterministic_extraction_extension_audit_v1_20260519.md`: PASS.

Final validation commands:
- `jq empty reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/extension_point_inventory.json reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/document_type_classifier_plan.json reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/no_regression_gate_map.json reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/status.json`: PASS.
- `git diff --check`: PASS.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/asx_deterministic_extraction_extension_audit_v1_20260519.md`: PASS, `ok=true`, `disallowed_files=[]`.
- `python3 scripts/agent_job_registry.py release asx_deterministic_extraction_extension_audit_v1_20260519`: PASS, `ok=true`.
- `python3 scripts/agent_job_registry.py list-active`: PASS, `active_jobs=[]`.
- `jq empty reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/diff-check.json reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/status.json`: PASS.

No extraction, live Docling, OCR, comparator, DB, Qdrant, runtime, GPU, memory, news, or Cockpit jobs were run.

## 14. Final Git Status

- `git status --short --untracked-files=all`: `?? docs/agent_tasks/asx_deterministic_extraction_extension_audit_v1_20260519.md`
- `git status --short --ignored=matching reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519`: `!! reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/`
- Interpretation: normal git status shows the task card only because this checkout ignores `reports/`; the report artifacts are present under the allowed output directory.

## 15. Registry Release Status

- Released. `status.json` reports `status=released`, `claimed_at=2026-05-20T00:51:33.538913Z`, `released_at=2026-05-20T01:04:05.562053Z`.
- Final `list-active` returned `active_jobs=[]`.

## 16. Project Memory Save Recommendation

Save a concise note that the ASX deterministic extraction extension audit concluded the safe path is fixture/schema and comparator-first: ASX document-type classifier sidecar, Appendix 5B/4C/4D/4E parser artifacts with `canonical_write=false`, no parser routing or canonical writes until canonical_core, expanded_required, and confirmed_metric_coverage gates pass. Also save that this branch lacks the standalone Appendix 5B scorer/gate stack and has no current MinerU/Chandra/TATR/pdfplumber comparator implementation.
