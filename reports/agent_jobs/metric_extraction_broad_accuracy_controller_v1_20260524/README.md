# Metric Extraction Broad Accuracy Controller v1

Lane: Financial Truth  
Supporting lane: Evaluation  
Branch: `migration/clean-runtime-baseline-reconstruct-v1`  
Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`  
Canonical path checked: `/home/l4nd0/tenn` resolves to this worktree  
Execution mode: AUDIT MODE  
Intended files: this parent task card and this report directory only  
Contested surfaces touched: none  
Collision risk: MEDIUM for report-only evaluation artifacts; HIGH parser/truth/runtime paths were not touched  
Decision: proceed audit-only

## Executive Result

The current repo evidence supports named, narrow evaluation profiles only. It does not support a broad metric extraction accuracy claim.

Confirmed profile state:

- `canonical_core`: 10 real-gold documents, 24 required metric checks.
- `expanded_required`: 15 real-gold documents, 39 required metric checks.
- `confirmed_metric_coverage`: 15 fixture files, 146 metric expectations, 73 scored-ready expectations, 70 candidate-review expectations, 3 ambiguous expectations, 0 unsupported expectations.

The current extraction surface supports the 10 multipass metric fields `revenue`, `ebit`, `np_attributable`, `operating_cf`, `investing_cf`, `financing_cf`, `capex`, `cash_end`, `net_debt`, and `shares_outstanding`. Some persistence and model surfaces also mention `total_equity`, `interest_expense`, and intermediate `total_debt`, but those are not part of the current real-gold/confirmed-coverage scorecard contract.

No canonical financial truth was written. No parser routing, Docling config, production extraction route, DB, Qdrant, memory store, runtime, GPU, Docker, cron, ingestion, backfill, reindex, or resync job was changed or run.

## Confirmed

- Preflight initially observed HEAD `b7be44463dd2107428d27165c564e62637576cdd`; while the repo was live, HEAD advanced to `e641db499b14dc53184eff678552b227a88dc573` by `milestone(evaluation): preserve quantdinger clean reprobe proof`. That drift touched Strategy Lab task/report files, not Financial Truth contested surfaces.
- The parent task card `docs/agent_tasks/metric_extraction_broad_accuracy_controller_v1_20260524.md` validates successfully and was claimed in the shared registry under `/mnt/sdb2/home/l4nd0/tenn/.git/tenn-agent-registry`.
- `docs/architecture/SYSTEM_CONTRACT.md` requires extraction to preserve explicit-source semantics: metric extraction must extract explicit values, return null when absent, avoid semantic fabrication, and only allow the documented Appendix 5B capex derivation.
- `multipass_extraction.py` defines 10 metric fields and a 4-pass flow: report context, deterministic table locator, LLM table/narrative extraction, then deterministic reconciliation.
- Real-gold evaluation is currently three required production metrics: `revenue`, `operating_cash_flow`/`operating_cf`, and `net_debt`. The expanded profile increases document count, not metric family breadth.
- Running the scorecard builder without extracted payloads produces inventory/quarantine state, not an accuracy result. A current extracted-payload scorecard for broad confirmed coverage is DATA_MISSING.
- Confirmed metric coverage is review/readiness inventory, not current broad accuracy: 73 rows are scored-ready, 70 require candidate review, and 3 are blocked as ambiguous.
- A read-only packet build showed all 146 confirmed-coverage rows currently lack local source PDFs in the active data root. Page/row/table metadata exists for many rows, but operator PDF opening is blocked until source files are available or explicitly marked DATA_MISSING.
- Appendix 5B has a current canonical-branch report artifact showing `gate_pass=true`, `canonical_write=false`, 7 scored documents, 5 pass, 0 fail, 13 trusted labelled metrics, 1.0 exact-match rate, and 1.0 labelled-metric coverage.
- Appendix 4C has classifier/comparator schema support and one classifier fixture, but no deterministic Appendix 4C parser/gate module was found in the current repo evidence.
- The Cockpit confirmed metric coverage UI is review-only: it can load/run review packets, export artifacts, show source metadata, and draft manual review decisions locally; it does not mutate canonical labels.

## Inferred

- The highest-risk broad-accuracy failure mode is overclaiming: current evidence can prove profile inventories and narrow gates, but cannot prove broad extraction correctness across all confirmed metric families without extracted payloads and source-verification gates.
- The most likely metric-specific risks are `net_debt` ambiguity/derivation, period-column selection, source-PDF availability, current-vs-comparative column confusion, unit/currency scale drift, sign handling for cash-flow and capex rows, and shares outstanding period-end vs weighted-average confusion.
- Appendix 4C should stay sidecar/report-only until a cash-flow-only fixture contract, candidate artifact schema, source binding, and no-regression gate exist.
- The offline normalizer/reporting work improves operator visibility, but it should continue to label canonical-core, expanded-required, and confirmed-coverage profiles separately.

## Speculative

- A future Appendix 4C prototype can probably reuse the Appendix 5B candidate/scorer pattern, but only as a deterministic sidecar with `canonical_write=false`.
- Some of the 70 candidate confirmed-coverage rows could become scored rows after source PDFs are restored and human review confirms the source evidence.
- `total_equity`, `interest_expense`, and `total_debt` may become useful evaluation families later, but promoting them now would require a separate scorecard contract and source-evidence review.

## DATA_MISSING

- No current generated broad confirmed-coverage accuracy scorecard with extracted payloads was found.
- No current `reports/extraction_eval` artifact was present in this checkout.
- No current source PDFs resolved for confirmed-coverage rows in the active data root during the read-only packet build.
- `graphify-out/GRAPH_REPORT.md` and `graphify-out/wiki/index.md` were not present in this checkout.
- A fresh Appendix 5B gate run was not executed under the parent card because the parent is audit-only and the existing canonical-branch report artifact was sufficient to map status.
- Production data, database rows, Qdrant, Tenn memory, company memory, market memory, thesis memory, and runtime state were intentionally not used.

## Validation

Validation is recorded in `status.json` after final checks. Parent-audit validation includes task-card validation, registry list/check-overlap/claim/release, JSON validation for generated artifacts, `git diff --check`, and task-card `check-diff`.

## Risks

- Operator verification is weakened while source PDFs are missing locally; the correct label for those rows is readiness/review inventory, not source-open verified accuracy.
- Historical baseline artifacts are useful context but not current proof of broad accuracy.
- Any child work that touches parser routing, production extraction, canonical truth, Docling behavior, scorecard labels, or memory stores returns to HIGH risk and must stop without separate approval.

## Next Safe Steps

1. Run a child audit to resolve confirmed-coverage source PDF availability and source-page openability without copying or mutating production data.
2. Run a child report-only gate refresh for Appendix 5B into a bounded report directory.
3. Create an Appendix 4C readiness child audit that drafts the cash-flow-only fixture/gate contract without parser routing changes.
4. Only after source verification, feed extracted payloads into the confirmed metric coverage scorer and report profile-specific accuracy separately from canonical-core and expanded-required.

## Files Inspected

- `CLAUDE.md`
- `docs/architecture/SYSTEM_CONTRACT.md`
- `docs/entrypoints.md`
- `docs/architecture/13_security_and_secrets.md`
- `docs/claude/STATE.md`
- `/home/l4nd0/.claude/projects/-mnt-sdb2-home-l4nd0-tenn/memory/MEMORY.md`
- `scripts/agent_job_contract.py`
- `scripts/agent_job_registry.py`
- `scripts/extraction_gold_eval_scorecard.py`
- `financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py`
- `financial-engine_v2/backend/app/services/extraction_eval.py`
- `financial-engine_v2/backend/app/services/extraction_gold_eval.py`
- `financial-engine_v2/backend/app/services/multipass_extraction.py`
- `financial-engine_v2/backend/app/services/method_isolated_extraction.py`
- `financial-engine_v2/backend/app/services/provenance.py`
- `financial-engine_v2/backend/app/services/docling_extract.py`
- `financial-engine_v2/backend/app/models/asx_financials.py`
- `financial-engine_v2/backend/app/services/pipeline.py`
- `financial-engine_v2/backend/app/services/validation/extraction_schemas.py`
- `financial-engine_v2/backend/tests/test_extraction_capability_guards.py`
- `financial-engine_v2/backend/app/main.py`
- `financial-engine_v2/backend/app/services/confirmed_metric_coverage_review.py`
- `cockpit-ui/components/cockpit/verification/tabs/metric-coverage-tab-panel.tsx`
- `cockpit-ui/components/cockpit/verification/tabs/gold-eval-tab-panel.tsx`
- `financial-engine_v2/backend/tests/test_confirmed_metric_coverage_api.py`
- `financial-engine_v2/backend/tests/test_confirmed_metric_coverage_review.py`
- `financial-engine_v2/backend/app/services/asx_document_type_classifier.py`
- `financial-engine_v2/backend/app/services/asx_comparator_artifact_schema.py`
- `financial-engine_v2/data/extraction_gold_real/README.md`
- `reports/agent_jobs/gold_metric_coverage_audit_v1_20260519/README.md`
- `reports/agent_jobs/gold_metric_coverage_audit_v1_20260519/metric_inventory.json`
- `reports/agent_jobs/gold_metric_coverage_audit_v1_20260519/scorecard_proposal.json`
- `reports/agent_jobs/gold_metric_coverage_eval_spine_normalizer_v1_20260524/README.md`
- `reports/agent_jobs/gold_metric_coverage_eval_spine_normalizer_v1_20260524/normalized_manifest.json`
- `reports/agent_jobs/appendix5b_fifth_doc_approval_packet_v1_20260517/README.md`
- `reports/agent_jobs/appendix5b_fifth_doc_approval_packet_v1_20260517/approval_packet.json`
- `reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/README.md`
- `reports/agent_jobs/appendix5b_backend_gate_services_restore_v1_20260517/promotion_decision.json`
- `reports/agent_jobs/appendix5b_prm_gate_stack_canonical_integration_v1_20260524/README.md`
- `reports/agent_jobs/appendix5b_prm_gate_stack_canonical_integration_v1_20260524/appendix5b_no_regression_report.json`
- `reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/README.md`
- `reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/deterministic_parser_plan.md`
- `financial-engine_v2/reports/extraction_baseline.json`

## Files Changed

- `docs/agent_tasks/metric_extraction_broad_accuracy_controller_v1_20260524.md`
- `reports/agent_jobs/metric_extraction_broad_accuracy_controller_v1_20260524/README.md`
- `reports/agent_jobs/metric_extraction_broad_accuracy_controller_v1_20260524/status.json`
- `reports/agent_jobs/metric_extraction_broad_accuracy_controller_v1_20260524/metric_extraction_coverage_map.json`
- `reports/agent_jobs/metric_extraction_broad_accuracy_controller_v1_20260524/metric_extraction_gap_register.json`
- `reports/agent_jobs/metric_extraction_broad_accuracy_controller_v1_20260524/safe_extension_candidates.json`
- `reports/agent_jobs/metric_extraction_broad_accuracy_controller_v1_20260524/no_regression_gate_plan.md`
- `reports/agent_jobs/metric_extraction_broad_accuracy_controller_v1_20260524/validation.json`
- `reports/agent_jobs/metric_extraction_broad_accuracy_controller_v1_20260524/diff-check.json`
