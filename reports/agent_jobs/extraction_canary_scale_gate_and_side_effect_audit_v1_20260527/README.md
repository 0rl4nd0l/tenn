# #96 Canary Scale Gate and Side-Effect Audit - 2026-05-27

## Verdict

Status: BLOCKED BEFORE SECOND CANARY BATCH.

No broad backfill was run by this audit. No second canary batch was submitted.
No production DB writes, direct SQL mutation, Qdrant/news/memory writes, service
restart, parser routing change, prompt change, gold-label mutation, schema
change, source PDF edit, or Cockpit UI change was made.

This job used the clean isolated worktree
`/home/l4nd0/tenn-extraction-canary-scale-gate-side-effect-audit-v1-20260527`
because the active baseline checkout had unrelated PR39/architecture dirt.

## Preflight

- Branch: `audit/extraction-canary-scale-gate-side-effect-audit-v1-20260527`.
- HEAD: `d85a8876594ac7f0a4389e0044d2597f1b2ae4e0`.
- Remote: `https://github.com/0rl4nd0l/tenn.git`.
- Initial isolated worktree status: clean.
- Baseline checkout dirt: unrelated architecture/PR39 files, left untouched.
- Registry check-overlap: PASS.
- Registry claim: PASS for
  `extraction_canary_scale_gate_and_side_effect_audit_v1_20260527`.
- Architecture rule note: `.cursor/rules/` is absent in this worktree. The audit
  used the task-card hard stops plus repo architecture docs
  `docs/architecture/06_embeddings_and_vector_store.md`,
  `docs/architecture/10_failure_model.md`,
  `docs/architecture/08_backfill_contract.md`, and
  `docs/architecture/12_evaluation_and_drift_monitoring.md`.

## PLS `scale_unknown` Root Cause

Classification: source document / candidate-selection mismatch.

The PLS document `918f0b4a-563b-4e53-962a-82f43882d667` is titled
`PLS - March 2026 Quarterly Activities Report advisory`. The source PDF is a
one-page advisory saying the March 2026 quarterly activities report is scheduled
for release on Friday, 24 April 2026. It is not the quarterly report itself.

The cached PyMuPDF extraction has one detected table, and that table is contact
details. There is no financial statement table and no unit-bearing header such
as `$'000`, `$m`, or `millions`. The persisted run
`78538206-a4ac-4bc2-8fa9-2f21094d70c9` therefore has:

- status `failed`
- error `validation_gate:scale_unknown`
- period type `Q`
- period end `2026-03-31`
- currency `AUD`
- scale `unknown`
- scale validation `pass`
- confidence metrics `0.0`
- zero non-null metrics
- empty row refs/provenance

Sub-question answers:

- Source table unit missing: YES. There is no financial table in the source PDF.
- Parser not carrying unit: NO current evidence. There was no unit to carry.
- Docling/PyMuPDF text extraction losing unit context: NO current evidence.
- Metric normalization refusing ambiguous value: YES, correctly.
- Document type/table mismatch: YES. The selected canary source is advisory-only.
- Missing contract rule: PARTIAL. The scale gate exists; the missing guard is
  upstream candidate filtering for advisory-only filings.

PLS correctly abstained/quarantined: it wrote zero financial rows, zero Qdrant
points, no risk-note row, no news/memory writes, and orders 3-10 were not
submitted after the failure.

## BHP Row and Evidence

BHP document `2fa98e79-9d34-4cc6-9977-bfc8e9b7eeb7` completed
`ok_low_confidence` with one financial row. This status is acceptable only as a
known native-currency/no-FX warning: the current policy stores non-AUD values
as-is and downgrades otherwise passing rows to `ok_low_confidence`.

Source URL:
`https://www.asx.com.au/asx/v2/statistics/displayAnnouncement.do?display=pdf&idsId=02981829`

Run context:

- run_id: `bdcbc76a-47ba-4370-95af-0462fdba1c86`
- requested method: `auto`
- actual method: `pymupdf`
- fallback used: `true`
- extractor: `docling_multipass_v1`
- model: `qwen2.5-14b-instruct`
- period: annual, `2025-06-30`
- payload period start: `2024-07-01`
- currency: `USD`
- scale: `millions`
- scale validation: `pass`
- confidence metrics: `1.0`

Persisted `ASXPeriodicFinancial` row:

| Metric | Value | Evidence |
| --- | ---: | --- |
| revenue | 55,658,000,000 | `income_statement:page_122:Revenue` |
| ebit | 17,537,000,000 | `income_statement:page_122:Profit from operations` |
| np_attributable | 7,897,000,000 | `income_statement:page_122:Attributable to BHP shareholders` |
| operating_cf | 18,692,000,000 | `cashflow_statement:page_83:Net operating cash flows` |
| investing_cf | -13,350,000,000 | `cashflow_statement:page_83:Net investing cash flows` |
| financing_cf | -5,971,000,000 | `cashflow_statement:page_83:Net financing cash flows` |
| capex | -9,398,000,000 | `cashflow_statement:page_83:Purchases of property, plant and equipment` |
| cash_end | 11,893,000,000 | `cashflow_statement:page_83:Cash and cash equivalents, net of overdrafts, at the end of the financial year 21` |
| net_debt | 12,924,000,000 | `net_debt_note:page_158:Net debt` |
| shares_outstanding | null | no provenance |
| total_equity | null | no provenance |
| interest_expense | null | no provenance |

Secondary observation: the run payload has `period_start=2024-07-01`, while the
persisted row has `period_start=null`. This was not one of the two canary
findings, so it remains follow-up only.

## `ASXRiskNote` Side Effect

Classification: bug; low immediate truth-contamination risk, but not harmless.

BHP has an `ASXRiskNote` row with all narrative fields null and
`confidence_narrative=0`, while the run summary reported
`risk_note_written: 0`.

Root cause:

- `_upsert_financial_rows()` unconditionally calls `_upsert_risk_note(...,
  allow_empty=True)` after financial-row handling.
- `_upsert_risk_note()` creates a row when `allow_empty=True`, even when
  `_has_narrative_content()` is false.
- `risk_note_written` is computed separately from narrative content, so it can
  honestly report `0` after an empty row has still been inserted.

Impact:

- It does not fabricate a narrative claim because all narrative fields are null.
- It can contaminate presence-based downstream checks that treat any
  `ASXRiskNote` row as a written risk note.
- The minimal code fix is narrow, but the required file is
  `financial-engine_v2/backend/app/services/pipeline.py`, which is outside the
  user-supplied and task-card allowlists. No production code fix was made.

## Safe Extension Made

Test-only safe extension: added
`financial-engine_v2/backend/tests/test_extraction_scale_gate.py`.

The test proves `scale=unknown` is a hard validation failure for a quarterly
payload before any financial truth write should be considered. No production
behavior was changed.

## Second Canary Decision

Second canary batch status: BLOCKED.

Required before orders 3-10:

1. Approve or apply the narrow empty-risk-note fix with an expanded allowlist
   that includes `financial-engine_v2/backend/app/services/pipeline.py`.
2. Remove or quarantine advisory-only filings like the PLS advisory from the
   canary candidate set before treating `scale_unknown` as a parser-scale defect.
3. Decide whether BHP native-USD `ok_low_confidence` is acceptable for canary
   progression as a known no-FX-policy warning.

## DATA_MISSING

- No broad candidate-set audit was run, so whether orders 3-10 contain other
  advisory-only filings is unknown.
- The empty-risk-note production fix was not applied because the exact root-cause
  file is outside the allowed files.
- `.cursor/rules/` architecture rule files are absent in this worktree.

## Validation

- Task-card validation: PASS.
- Registry list-active and check-overlap: PASS.
- Registry claim: PASS.
- Read-only SQL inspection of the two canary document/run records: PASS.
- Focused pytest: PASS, 3 passed.
- `py_compile` touched Python file: PASS.
- Ruff touched Python file: PASS.
- JSON validation: PASS.
- `git diff --check`: PASS.
- Task-card check-diff: PASS, no disallowed files.
- Source PDFs staged: none.
- Registry release: PASS.
- Final registry list-active: PASS, no active jobs.
- Broad backfill run: no.
- Second canary batch run: no.

## GitHub

A concise issue #96 update was prepared in
`github_issue_96_comment.md`. If posted, it must remain comment-only: do not
close, relabel, assign, milestone, or edit the issue.

Posted comment:
`https://github.com/0rl4nd0l/tenn/issues/96#issuecomment-4552883625`.

## Project Memory Recommendation

Save that the first #96 canary retry proved the PyMuPDF cache-path blocker fixed
for the live route, but the second canary batch remains blocked. PLS was an
advisory-only false-positive candidate that correctly failed
`validation_gate:scale_unknown` without writing financial truth. BHP exposed a
narrow empty-`ASXRiskNote` side effect rooted in `pipeline.py`, but the fix needs
explicit allowlist expansion.
