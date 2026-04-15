---
type: analysis
title: Phase 02 Extraction Accuracy Backlog
created: 2026-04-15
tags:
  - extraction
  - eval
  - backlog
related:
  - '[[phase-01-prototype-report]]'
  - '[[phase-02-accuracy-report]]'
---

# Phase 02 Accuracy Backlog

## Scope

This backlog ranks the next reusable backend extraction fixes using confirmed evidence from the current synthetic eval lane, the current real-gold corpus artifacts, the existing review-session outputs, and the extraction implementation/tests that already cover these paths.

Evidence reviewed for this backlog:

- `docs/ops/extraction-truth/[[phase-01-prototype-report]]`
- `reports/extraction_real_eval_summary_runtime_hardened_2026-04-15.md`
- `reports/extraction_real_eval_results_runtime_hardened_2026-04-15.json`
- `reports/extraction_real_eval_results_after_p0.json`
- `reports/extraction_real_eval_summary.md` from the limited Phase 01 proof rerun
- `financial-engine_v2/backend/tests/eval_results/eval_2026-04-13T074232Z.json`
- `financial-engine_v2/backend/tests/eval_results/eval_progress_2026-04-13T063127Z.json`
- `financial-engine_v2/backend/app/services/multipass_extraction.py`
- `financial-engine_v2/backend/app/services/docling_extract.py`
- `financial-engine_v2/backend/tests/test_multipass_extraction.py`
- `financial-engine_v2/backend/tests/test_extraction_eval.py`
- `financial-engine_v2/backend/tests/test_extraction_gold_eval.py`
- `financial-engine_v2/backend/tests/test_prose_shares_extraction.py`

## Parser-Path Failure Comparison

The following table compares failures across the three key eval snapshots to distinguish docling-specific, pymupdf-specific, and both-path failures.

| Document | Metric | docling (corpus_v2) | pymupdf (corpus_v2) | runtime_hardened (2026-04-15) | Parser confirmed |
| --- | --- | --- | --- | --- | --- |
| bhp_a_2025-06-30 | revenue | wrong (+4.396B) | wrong (+4.396B) | wrong (+4.396B) | both paths |
| bhp_a_2025-06-30 | net_debt | missing | missing | missing | both paths |
| bhp_a_2021-06-30_difficult | net_debt | wrong (+1.616B) | missing | correct ✓ | FIXED in Phase 01 |
| qbe_h_2025-06-30 | operating_cash_flow | missing | ok | correct ✓ | FIXED in Phase 01 |
| rio_a_2024-12-31 | revenue | ok | missing | correct ✓ | FIXED in Phase 01 |
| tls_h_2025-12-31 | net_debt | missing | ok | correct ✓ | FIXED in Phase 01 |
| min_h_2025-12-31 | net_debt | not in gold (no failure) | not in gold (no failure) | wrong (null≠4.878B) | gold corpus gap |
| gre_q_2024-12-31 | operating_cash_flow | ok | wrong (scale_unknown) | correct ✓ | pymupdf-only |
| gre_q_2025-09-30 | operating_cash_flow | ok | wrong (scale_unknown) | correct ✓ | pymupdf-only |
| eqr_q_2025-12-31 | operating_cash_flow | ok | wrong (scale_unknown) | correct ✓ | pymupdf-only |

**Key observations:**
- BHP FY25 is the only document failing on **both** parser paths, and it fails on the same two metrics across all three snapshots. This is the highest-confidence real failure.
- Scale-unknown failures on quarterly documents (GRE, EQR) were confined to pymupdf and are resolved in runtime_hardened.
- MIN H1 FY26 net_debt appears only in the runtime_hardened run because the gold corpus was updated to add `net_debt=null` between the corpus_v2 and runtime_hardened snapshots. This needs a gold corpus verification pass rather than an extractor fix.
- BHP FY21 "difficult" is currently returning **trusted** (all metrics correct) but gold says `expected_trust=abstain`. This is a stale gold corpus field, not an extractor error.

## Ranked Backlog

| Rank | Failure class | Confirmed evidence | Suspected root cause | Why this order |
| --- | --- | --- | --- | --- |
| 1 | BHP FY25 annual current-period selection is still pulling the wrong revenue and dropping net debt under the PyMuPDF fallback path | Real-gold runtime-hardened run on 2026-04-15 shows `bhp_a_2025-06-30` as `abstain` instead of `trusted`, with `revenue` wrong (`55.658B` vs `51.262B`) and `net_debt` missing while `operating_cash_flow` remains correct. The same document was also wrong in `reports/extraction_real_eval_results_after_p0.json`, so this is a persistent live-document failure class rather than a one-off transient. | Likely a combination of annual-summary table selection and current-period column choice drift when the parser backend is `pymupdf`, plus missing explicit net-debt note capture when the fallback parser owns the table surfaces. This is an inference from the mixed `revenue:wrong` plus `net_debt:missing` pattern and the `actual_method=pymupdf` provenance. | Highest downstream value: this is a real-gold `trusted` document currently blocking the lane and it hits both top-line truth and leverage truth in one annual-report pattern. |
| 2 | Net debt still has a live abstain/over-extraction split across annual and half-year statements | Real-gold runtime-hardened run has the worst per-metric failure count on `net_debt` (`1 wrong`, `1 missing`). `min_h_2025-12-31` is still `abstain` because `net_debt` was extracted as `4.878B` where gold expects `null`, while `bhp_a_2025-06-30` still misses `net_debt` entirely. Synthetic eval also keeps `net_debt` at `0.6429` in `eval_2026-04-13T074232Z.json`. | The code already mixes three paths for net debt: explicit note extraction, explicit summary-table extraction, and deterministic derivation from `total_debt - cash_end`. The remaining failures suggest inconsistent gating between “explicit enough to emit” and “ambiguous so abstain,” especially when row refs degrade to generic debt labels or when parser differences hide the explicit note. | This is the most repeated live failure class after the BHP annual case, and it directly changes trust outcomes that feed downstream analysis. |
| 3 | Shares-on-issue extraction remains the broadest synthetic accuracy gap and still needs a cross-format hardening pass | The latest full synthetic eval keeps `shares_outstanding` at `0.5`, the lowest metric score in `eval_2026-04-13T074232Z.json`. Existing targeted fixtures and tests already isolate recurring patterns: `shares_fallback_disagreement`, SEG row-label `No. '000s` scaling, weighted-average rejection, dollar-denominated share-capital rejection, absolute-count preservation, stapled security counts, and prose fallback priority. | The core issue appears to be parser/layout sensitivity in count detection rather than missing infrastructure: row-label scaling, header-vs-body unit signals, and share-count vs dollar-capital discrimination are already implemented but still brittle across diverse layouts. | This is the largest unresolved synthetic gap and has high downstream impact because `shares_outstanding` feeds EPS and EV-style analysis, but it ranks behind the real-gold failures that already flip trust. |
| 4 | Current-period column selection and filtered-table retry need to be treated as one reusable failure family, not isolated prompt text | The synthetic fixture `wrong_current_period_column` remains an explicit negative-path guard, and the extractor tests already require `period_end` to appear in prompts and force a full-table retry when filtering hides a key metric. The same family likely explains part of the BHP FY25 revenue drift, because the document is wrong on `revenue` but correct on `operating_cash_flow`, which points to table/column choice rather than a global scale or currency failure. | Existing defenses are split across prompt instructions, `period_col` propagation, row filtering, and full-table retry. The remaining gap is likely not “missing logic” so much as inconsistent selection when summary tables and fallback parser tables both qualify. This is an inference from the current code/test split. | Fixing this as a shared selector problem should remove several revenue/EBIT/capex classes at once instead of chasing single-ticker outputs. |
| 5 | Quarterly structural docs still have an extraction-status inconsistency even when the gold metric lane passes | In the runtime-hardened real-gold run, `gre_q_2025-09-30` is `trusted` with correct `operating_cash_flow`, but the document still records `extraction_status=failed` because the validation gate returns `validation_gate:insufficient_metrics:2`. Synthetic tests explicitly treat quarterly Appendix 5B docs as structurally limited and expect missing income-statement metrics to stay null. | The generic validation gate still enforces `len(non_null) < 3` before it considers document type, so quarterly cash-flow-only documents can be “metric-correct” yet still inherit a failed extraction status. | This is lower risk than the metric-truth bugs because trust remains correct, but it is a reusable inconsistency that will keep confusing operators and reports. |
| 6 | Non-AUD truth handling should be monitored, not reworked, unless a fresh inconsistency appears | The 2026-04-15 runtime-hardened real-gold run achieved `100%` context accuracy across USD and AUD documents, with QBE and both RIO annuals now trusted. Historical artifacts show why this still belongs on the backlog edge: the limited Phase 01 proof quarantined `bhp_a_2021-06-30_difficult` on parser failure, and `reports/extraction_real_eval_results_after_p0.json` previously quarantined EQR on a currency mismatch. | Current code already downgrades non-AUD payloads to `ok_low_confidence` without FX conversion and keeps raw currency context intact. The remaining risk is regression in detection/labeling rather than a missing FX feature, and any “fix” must not introduce AUD conversion or cross-company normalization. | Keep as a guardrail item only. The current evidence says the truthful non-AUD path is mostly behaving and should not displace the higher-value metric fixes above. |

## Attack Order Notes

1. Fix the BHP FY25 annual path first and treat it as the anchor case for both current-period selection and missing net-debt handling under parser fallback.
2. Harden net-debt emission rules second so explicit-note extraction, summary-table extraction, and deterministic derivation agree on when to emit vs abstain.
3. Use the existing SEG and share-capital cases to tighten `shares_outstanding` without adding manual overrides or Cockpit-side patches.
4. After the metric fixes, resolve the quarterly validation-gate inconsistency so correct Appendix 5B documents are no longer marked failed.

## Gold Corpus Corrections Needed

The following gold corpus entries are suspected stale or incorrect based on current eval evidence. These must be verified against source PDFs before updating.

| Document | Field | Current gold value | Runtime_hardened actual | Suspected correction |
| --- | --- | --- | --- | --- |
| bhp_a_2021-06-30_difficult | expected_trust | abstain | trusted (all metrics correct) | Update to `trusted` once confirmed via source PDF |
| min_h_2025-12-31 | net_debt | null | 4,878M AUD (extracted) | Verify source PDF: if MIN reports net_debt explicitly, update gold to 4,878M AUD and adjust expected_trust |

Until verified by hand against the source PDFs, neither of these should be changed — they represent genuine open questions about document-level truth.

## De-prioritized Or Resolved Since Earlier Artifacts

- The Phase 01 limited proof rerun (`reports/extraction_real_eval_summary.md`) was dominated by a single parser-error quarantine for `bhp_a_2021-06-30_difficult`. The broader runtime-hardened run on 2026-04-15 shows that parser/context issue is no longer the main blocker: the same document now has correct metric values and correct context, with only an expected-trust mismatch remaining.
- Earlier real-gold artifacts also showed non-AUD context mismatches such as EQR quarantining on currency. That issue does not appear in the current runtime-hardened run, so Phase 02 should not spend its first edits on currency conversion or aggressive context rewiring.

## Contract Note

This backlog stays inside the backend extraction lane:

- no Cockpit-side truth adjustment
- no post-hoc manual overrides
- no unsafe derivation beyond the already documented deterministic paths
- no FX conversion work beyond truthful native-currency preservation and labeling
