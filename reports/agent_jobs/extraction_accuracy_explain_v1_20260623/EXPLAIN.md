# Why Accurate Extraction Is Not Solved Yet

Generated: 2026-06-23

## Headline

Tenn cannot honestly claim broad accurate financial extraction yet because the
system is still missing two things at the same time:

1. A current, source-bound extracted-payload scorecard over a known denominator.
2. End-to-end row-level proof for the remaining hard document and metric
   classes before values are promoted as truth.

Recent work fixed important blockers: JAY market-update revenue is now
source-bound, pytest fallback works, and the no-write replay harness completed
the targeted JAY, guard, and WHC/EDU replays. That is regression progress. It is
not the same as broad extraction accuracy.

## What It Is

Financial extraction is the path that turns ASX PDFs into canonical metrics such
as revenue, EBIT, NPAT, cash flow, capex, cash, debt, shares, period, currency,
and scale.

For Tenn, an extracted value is not accurate just because the model emits a
number. It needs:

- the right source document;
- the right document class;
- the right page/table/row/period/column;
- the right metric meaning;
- the right scale and currency;
- a row reference and provenance;
- a validation gate that can accept, abstain, quarantine, or fail closed;
- scorecard proof against an approved expected value.

## Why It Exists

The project is intentionally conservative because bad financial truth is worse
than missing financial truth. A wrong EBIT, revenue, or cash-flow number can
pollute downstream analysis, search, memory, and investor-facing answers.

The design target in issue #73 is an evidence-bound pipeline:

```text
PDF
-> document classifier
-> layout/table extraction
-> document-type-specific extractors
-> metric normalization
-> evidence binding
-> validation/reconciliation
-> scored eval artifacts
-> canonical write only if trusted
```

That is the right architecture. The system is only partially through that path.

## Current State

- VERIFIED: origin has moved to `f195e90d464f49916f6626242ca26d74580dc0a1`.
  The commit after the validation refresh touched control-plane ledger/reporting
  docs, not extraction product code.
- VERIFIED: PR #384 is merged and JAY market-update revenue remains green in
  canonical replay evidence.
- VERIFIED: the post-PR384 validation refresh passed:
  - JAY canonical no-write replay: `PASS`, 2 cases, side effects clean.
  - compatible guard replay: `PASS`, 5 cases, side effects clean.
  - WHC/EDU mixed-unit replay: `PASS`, 2 cases, expected fail-closed behavior,
    side effects clean.
  - focused JAY pytest target: `PASS`, `3 passed, 204 deselected`, via
    ephemeral pytest overlay.
- VERIFIED: active/unproven row residuals remain:
  - DXC `metric_label_mismatch`: `NO_FIX_PROVEN`.
  - WHC 2022 `scale_unknown / openability`: source-row scale proof still
    required.
- VERIFIED: issue #73 remains open as the ASX evidence-bound extraction parent
  tracker.
- VERIFIED: issue #96 remains open for runtime coverage/backfill/file
  availability. Its 2026-05-26 evidence showed broad document inventory but
  narrow current-version terminal extraction and financial-row coverage.
- VERIFIED: issue #97 remains open because confirmed metric expectations are
  not yet scored against current extracted payloads.
- DATA_MISSING: this run did not execute a fresh production DB coverage probe,
  a full count sample, a count-24/count-32 rerun, or full-universe extraction.
  Therefore there is no current verified broad accuracy percentage from this
  run.

## Ledger And Duplicate-Work Status

- VERIFIED: read-only registry check found one active job:
  `repo_dev_import_runtime_entrypoint_remediation_v1_20260623` in another
  worktree. It is Evaluation/control-plane work, not this explanation.
- DATA_MISSING: live task ledger file was unavailable.
- VERIFIED: committed ledger was present and valid.
- VERIFIED fallback search: task cards, report bundles, open PRs, open issues,
  worktrees, and relevant paths were searched.
- VERIFIED related work:
  - PR #340: WHC OCR/openability probe packet, related but not a complete broad
    extraction fix.
  - PR #131: older metric ontology/gate branch, related but not current proof
    that broad extraction is accurate.
  - issues #73, #96, #97 remain the main live trackers.

## What Changed Recently

- JAY market-update recovery was added and validated. `Net Revenue` rows now
  recover canonical `revenue` for Q3/Q4 FY2023 market-update documents without
  inventing absent cash-flow, balance-sheet, annual, or profit metrics.
- The pytest failure mode was remediated with `run_pytest_with_fallback.py`.
  Missing pytest no longer blocks focused validation if a runtime venv exists.
- No-write replay now has a per-case timeout, so Docling/LLM hangs are supposed
  to become structured artifacts instead of indefinite stalls.
- WHC/EDU mixed-unit accepted outputs now fail closed instead of passing unsafe
  values.

## What Is Broken

### 1. The Denominator Is Not Current

Issue #96's historical runtime evidence showed many PDF-path documents lacked
terminal current-version extraction and many tickers lacked financial rows.
This run did not re-probe the DB, so the current exact denominator is
`DATA_MISSING`.

Consequence: we cannot say "accuracy is X%" because we have not freshly traced
raw documents -> candidates -> terminal extracted payloads -> scored outputs.

### 2. The Scorecard Is Not Feeding Current Extracted Payloads

Issue #97 says confirmed expectations exist, but broad runtime accuracy remains
`DATA_MISSING` until current extracted payloads are scored against them.

Consequence: inventory and fixture presence are not accuracy. A payload has to
be compared to expected source-bound values per metric.

### 3. PDFs Are Not One Document Type

Annual reports, half-year reports, Appendix 4D/4E, Appendix 5B, results
presentations, market updates, quarterly reports, and advisory documents expose
financial data differently.

Consequence: one generic prompt/parser behavior will keep failing edge cases.
The right fix is document-class routing and class-specific extraction/validation.

### 4. Table Extraction And Openability Are Uneven

Some documents need selected statement pages/tables, OCR/openability help, or
Docling-native table evidence. WHC 2022 remains a representative source-scale
and openability proof problem.

Consequence: if the parser cannot prove the exact row/header/table, the system
must abstain or fail closed.

### 5. Metric Labels Are Ambiguous

`Net operating income` is not automatically canonical EBIT. EBITDA is not EBIT.
Industry-specific operating-profit labels can be valid in one context and wrong
in another.

Consequence: broad label mapping is dangerous. DXC needs exact source-row proof
before any ontology or validator change.

### 6. Scale Is A Per-Row / Per-Table Problem

Documents can mix `$000`, `$m`, raw dollars, shares, operational units, and
presentation-scaled values. WHC/EDU proved that unsafe scale/magnitude outputs
must fail closed.

Consequence: document-level scale is not enough. The extractor needs
metric-level source scale binding and confidence.

### 7. Provenance Is Still Not Complete Enough

Some replay outputs still contain `unknown` row refs for derived or cash-flow
metrics. Older accepted-output artifacts omitted exact row refs/provenance.

Consequence: a number without source-row evidence should not become canonical
truth.

## Risks

- A one-off PDF fix can improve one replay and damage another document class.
- Broad prompt changes can make the model more confident while reducing truth.
- Mapping ambiguous labels globally can create false EBIT/revenue/cash-flow
  facts.
- Treating green no-write replays as broad accuracy would overclaim. The recent
  replay set is regression evidence, not full corpus proof.
- Report-only work can become a loop unless every proof lane ends in one of
  `FIX_PROVEN`, `NO_FIX_PROVEN`, or `DATA_MISSING`.

## Zoom-Out Answers

Are we solving the real root problem?

Partly. The validation-environment blocker is solved for the targeted sample.
JAY is solved. But broad accuracy still needs measurement, coverage, row proof,
and document-class repairs.

Are we overfitting to one file or artifact?

There is still a risk. The correct next work must target failure classes:
runtime coverage, scorecard actuals, source-row metric mismatch, scale binding,
and document-class extraction.

Are we trapped in report-only loops?

Not if reports are treated as gates. The next row-proof and scorecard lanes
must produce either a proven fix, a proven no-fix, or named missing data.

Are we making broad system progress?

Yes, but in layers: validation safety improved; one residual retired; mixed-unit
unsafe outputs now fail closed. The broad layer is still open because #96 and
#97 are not done.

Would a class-based approach be better than another narrow fix?

Yes. The next fixes should be failure-class and document-class driven, not
"patch this one PDF."

What is the best next action by production-readiness value?

Run a measurement-first extraction sprint that refreshes runtime coverage and
extracted-payload scoring, then fixes the top failure classes with exact
source-row proof.

## What Needs To Be Done

### Phase 1: Measure The Current System

Use issue #96 and #97 as the controlling trackers.

- Run a fresh read-only runtime coverage probe:
  - raw documents;
  - documents with PDF paths;
  - files existing on this host;
  - terminal extraction rows by extractor version;
  - failed/skipped/not-run states;
  - financial rows by ticker/document class.
- Run current extracted payloads through the confirmed metric scorecard:
  - exact match;
  - tolerated numeric match;
  - missing;
  - null/abstain;
  - unsupported;
  - quarantine.
- Keep profiles separate:
  - `canonical_core`;
  - `expanded_required`;
  - `confirmed_metric_coverage`.

Output: a current denominator and failure matrix. No product fix should happen
before this matrix exists unless it is a narrow source-proven residual.

### Phase 2: Fix Row-Proof Residuals

Start with DXC and WHC because they are active residuals after the post-PR384
refresh.

- DXC:
  - capture exact source rows around `net operating income`;
  - record page/table/row/period/unit/value/context;
  - decide whether it is canonical EBIT, industry-specific operating income,
    or not safely mappable;
  - end as `FIX_PROVEN`, `NO_FIX_PROVEN`, or `DATA_MISSING`.
- WHC:
  - use PR #340 as related evidence, but verify from current source artifacts;
  - capture exact table headers and row-level scale metadata;
  - prove whether per-metric source scale can be bound safely;
  - otherwise keep fail-closed.

### Phase 3: Promote Document-Class Extractors

Treat ASX document families separately:

- Appendix 5B and 4C: deterministic form parsers where form structure allows.
- Appendix 4D/4E: wrapper/statement-aware extraction with disclosure checks.
- Annual/half-year reports: statement table selector plus row/scale/period
  binding.
- Presentations and market updates: narrow source-bound patterns only; no broad
  inference from marketing slides.
- Advisory/noncandidate documents: pre-extraction exclusion or fail closed.

### Phase 4: Strengthen Provenance

Every accepted metric should carry:

- source document ID;
- page/table identifier when available;
- row label;
- period/column;
- unit/scale/currency;
- value before and after scaling;
- metric ontology mapping;
- confidence and validation gate status.

Unknown row refs should become a visible risk class. They may be acceptable for
derived metrics only when the derivation inputs are proven.

### Phase 5: Gate Canonical Writes

Promotion to canonical financial truth should require:

- source-bound evidence for every promoted value;
- no-regression on guard cases;
- scorecard pass for the relevant profile;
- fail-closed behavior for ambiguous values;
- reviewed promotion criteria.

Until then, outputs should remain report-local, quarantined, or abstained.

## Practical Next Goal

Create a fresh task card from current
`origin/migration/clean-runtime-baseline-reconstruct-v1` and run a
measurement-first extraction sprint:

1. Refresh #96 runtime coverage counts read-only.
2. Refresh #97 extracted-payload scorecard on the approved confirmed metric
   fixture set.
3. Produce a ranked failure-class matrix.
4. Run exact source-row proof for DXC and WHC.
5. Implement only the top source-proven failure-class fix.

Hard stop: no broad prompt, parser, ontology, classifier, DB, Qdrant, source
PDF, gold-label, model/runtime, or canonical-write change from ambiguous
evidence.
