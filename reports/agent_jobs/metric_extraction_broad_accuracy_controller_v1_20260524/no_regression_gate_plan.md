# Metric Extraction No-Regression Gate Plan

This plan defines the smallest gates required before claiming any expansion of Tenn metric extraction coverage. It is intentionally profile-specific. It does not authorize canonical truth writes, parser routing changes, Docling configuration changes, prompt broadening, ingestion, backfill, runtime changes, or memory-store writes.

## Global Gates

Every metric extraction promotion task must prove:

1. Valid task card with `production_data_access: false` unless explicitly approved otherwise.
2. Registry `list-active` and `check-overlap` show no unresolved HIGH collision.
3. Exact branch, HEAD, worktree, dirty state, and input tuple are recorded.
4. Profile name is present on every score: `canonical_core`, `expanded_required`, `confirmed_metric_coverage`, Appendix 5B gate, or Appendix 4C prototype.
5. Source binding classification is explicit: precise, derived, low-traceability, missing, candidate, ambiguous, or DATA_MISSING.
6. No candidate, ambiguous, unsupported, missing-source, or inventory-only count is converted into an accuracy numerator.
7. JSON artifacts validate and `git diff --check` passes.

## Canonical Core

Minimum promotion gate:

- Dataset/profile: `canonical_core`.
- Current contract: 10 documents, 24 required metric expectations.
- Eligible metric families: `revenue`, `operating_cash_flow`/`operating_cf`, `net_debt`.
- Required context gates: ticker, report type, period end, period type, currency, and scale.
- Required result labels: correct, wrong, missing, abstain, quarantine.
- Hard gate: any context mismatch quarantines the payload and blocks trust.
- Output must include provenance summary and per-metric source status.

Hard stops:

- Do not add extra metric families to this profile without a separate scorecard contract.
- Do not count a historical baseline as current proof.

## Expanded Required

Minimum promotion gate:

- Dataset/profile: `expanded_required`.
- Current contract: 15 documents, 39 required metric expectations.
- Metric family scope remains the same as canonical core.
- Document-count expansion must be reported separately from metric-family expansion.

Hard stops:

- Do not describe expanded-required success as broad financial metric accuracy.
- Do not score non-required confirmed metrics in this profile.

## Confirmed Metric Coverage

Minimum readiness gate:

- Fixture inventory exists and validates.
- Current observed fixture count: 15.
- Current observed expectation count: 146.
- Current observed scored-ready expectations: 73.
- Current observed candidate-review expectations: 70.
- Current observed ambiguous expectations: 3.
- Current observed unsupported expectations: 0.
- Candidate, ambiguous, missing-source, and unsupported rows remain outside scored accuracy.
- Source PDF availability is checked and either verified openable or explicitly marked DATA_MISSING.

Minimum accuracy gate:

- Extracted payloads are supplied to the scorer under a child task.
- Only the 73 scored-ready expectations can enter the initial denominator unless human review promotes additional rows.
- Candidate rows require human source-evidence review before scoring.
- Ambiguous rows must remain excluded until ambiguity is resolved by a separate label-review process.
- Results must preserve profile name and denominator in every summary.

Hard stops:

- Do not claim broad accuracy from readiness inventory.
- Do not mutate canonical labels from Cockpit draft decisions.
- Do not weaken source-route allowlists to make PDFs open.

## Appendix 5B PRM/Fifth-Doc Floor

Minimum gate before more Appendix 5B expansion:

- Run the existing no-regression gate into a child report directory.
- Required command shape:

```bash
PYTHONPATH=financial-engine_v2/backend python3 scripts/run_appendix5b_no_regression_gate.py --output reports/agent_jobs/<child_job_id>/appendix5b_no_regression_report.json
```

- If using the wrapper, also run:

```bash
PYTHONPATH=financial-engine_v2/backend python3 scripts/run_extraction_evaluation_gates.py --only appendix5b_prm_no_regression --output reports/agent_jobs/<child_job_id>/evaluation_gates_report.json
```

Minimum pass criteria:

- `canonical_write` is false.
- `gate_pass` is true.
- `failed_checks` is empty.
- Documents scored are explicitly reported.
- Document pass/fail/unscored counts are explicitly reported.
- Labelled metric count and trusted metric count are explicitly reported.
- Exact-match rate and labelled-metric coverage are 1.0 for promotion language.
- Expected-null cases are explicitly respected.

Current artifact floor from the canonical integration report:

- `gate_pass=true`.
- `canonical_write=false`.
- `documents_scored=7`.
- `document_pass=5`.
- `document_fail=0`.
- `labelled_metric_count=13`.
- `trusted_metric_count=13`.
- `exact_match_rate=1.0`.
- `labelled_metric_coverage=1.0`.

Hard stops:

- Do not run production extraction.
- Do not write canonical truth.
- Do not change parser routing.
- Do not broaden capex derivation beyond the documented Appendix 5B allowance.

## Appendix 4C Prototype

Minimum readiness gate before implementation:

- Classifier fixture confirms Appendix 4C document type.
- Comparator artifact schema validates Appendix 4C cash-flow candidates.
- The prototype contract is cash-flow-only.
- Revenue, NPAT, net debt, EPS, ratios, margins, and segment metrics are explicitly forbidden in Appendix 4C sidecar artifacts unless a separate source-bound contract is approved.
- Current quarter and year-to-date values are distinct fields.
- Page, table, row, column, unit, currency, period, and sign are captured in the artifact.
- `canonical_write=false`.

Hard stops:

- Do not add parser routing in the readiness audit.
- Do not infer income-statement or balance-sheet metrics from Appendix 4C.
- Do not promote to canonical truth without a separate no-regression gate.

## Cockpit Verification Gates

Minimum operator-safety gate:

- Confirmed metric coverage review UI must preserve review-only language.
- Source page links must use the backend allowlisted source route.
- If the source PDF is missing, the row must remain DATA_MISSING or source-unopenable.
- Draft manual review decisions must not mutate canonical labels.
- Gold eval UI must show dataset/profile/method context beside any score.

Hard stops:

- Do not label no-row evidence as source-backed.
- Do not collapse candidate/ambiguous rows into confirmed rows for display.
- Do not remove profile labels from score summaries.

## Reporting and Normalization Gates

Minimum gate:

- Normalized artifacts preserve separate sections for canonical core, expanded required, and confirmed metric coverage.
- Missing current accuracy remains DATA_MISSING.
- Historical baseline artifacts are clearly labelled historical.
- Output JSON validates.

Hard stops:

- Do not combine profile denominators into a single broad score.
- Do not use normalizer output as proof of extraction correctness.

## Final Promotion Rule

Broad financial metric extraction accuracy can be claimed only when:

1. The target metric families and document types are explicitly named.
2. Extracted payloads are scored against source-bound labels.
3. Candidate and ambiguous rows are excluded or separately promoted by reviewed evidence.
4. Source PDFs or equivalent source evidence are available and verified.
5. Canonical-core and expanded-required no-regression gates still pass.
6. All scorecards are profile-labelled and reproducible from committed artifacts.
