---
type: report
title: Phase 02 Extraction Accuracy Report
created: 2026-04-15
tags:
  - extraction
  - eval
  - report
  - phase-02
related:
  - '[[phase-02-backlog]]'
  - '[[phase-01-prototype-report]]'
---

# Phase 02 Accuracy Report

## Outcome

Phase 02 landed five hardening categories in `multipass_extraction.py` and added 62 new unit/regression tests, bringing the total Phase 02 test scope to 196 passing tests across 6 files. No live LLM re-evaluation was run during Phase 02 — the baseline comparison uses the last live eval (`eval_2026-04-13T074232Z.json`) as pre-phase state, and the runtime-hardened real-gold run from 2026-04-15 as the best available real-document comparison point.

All Phase 02 ruff lint checks pass. No eval_config.json thresholds were changed — there is no verified corpus delta yet to justify a threshold update.

---

## Comparison Snapshots Used

| Snapshot | Source | When |
| --- | --- | --- |
| Pre-Phase-02 synthetic baseline | `eval_results/eval_2026-04-13T074232Z.json` | 2026-04-13 (last live eval) |
| Post-Phase-01 real-gold run | `reports/extraction_real_eval_results_after_p0.json` | 2026-04-15 (Phase 01 end) |
| Runtime-hardened real-gold run | `reports/extraction_real_eval_results_runtime_hardened_2026-04-15_summary.json` | 2026-04-15 (hardened backend) |

---

## Real-Gold Delta (Phase 01 end → runtime-hardened)

The runtime-hardened run reflects the same hardening sprint as Phase 02. This is the best available real-document accuracy comparison.

| Metric | Phase 01 end | Runtime-hardened (2026-04-15) | Direction |
| --- | --- | --- | --- |
| Total accuracy (real-gold, 10 docs) | 0.625 | **0.875** | ↑ +0.250 |
| Context accuracy | 0.900 | **1.000** | ↑ +0.100 |
| Trusted documents | 3 / 10 | **8 / 10** | ↑ +5 |
| Abstained documents | 6 / 10 | **2 / 10** | ↓ −4 |
| Quarantined documents | 1 / 10 | **0 / 10** | ↓ −1 |
| Metric correct count | 15 / 24 | **21 / 24** | ↑ +6 |
| Metric missing count | 6 / 24 | **1 / 24** | ↓ −5 |
| Metric wrong count | 3 / 24 | **2 / 24** | ↓ −1 |

### Remaining real-gold failures

Both remaining failures are confined to `bhp_a_2025-06-30`:

| Document | Metric | Status | Root cause |
| --- | --- | --- | --- |
| `bhp_a_2025-06-30` | `revenue` | wrong (+4.396B vs expected 51.262B) | Current-period column selection pulls summary consolidated row instead of pure operating revenue — both parser paths affected |
| `bhp_a_2025-06-30` | `net_debt` | missing | Net debt lives in a note/supplementary table that neither pymupdf nor docling surfaces for this document layout |

These are the Rank 1 and Rank 2 items from [[phase-02-backlog]] and remain open for Phase 03.

---

## Synthetic Eval Baseline Delta

A new live synthetic eval was not run during Phase 02 (requires llama.cpp server active). The following pre-Phase-02 baselines are recorded for comparison when the next eval run is triggered:

| Metric | Pre-Phase-02 (2026-04-13) | Phase 02 code change | Expected direction |
| --- | --- | --- | --- |
| Overall accuracy | 0.8533 | — | ↑ (shares, net_debt fixes) |
| `shares_outstanding` | 0.500 | Evidence scan extended to all body rows; absolute count ≥1M bypass added | ↑ expected |
| `net_debt` | 0.6429 | Derived-row fragments + movement patterns rejected | ↑ expected |
| `ebit` | 0.6923 | No change in Phase 02 | → unchanged |
| `operating_cf` | 1.000 | Quarterly gate fixed (min 1 metric for 5B docs) | → stable |
| `revenue` | 0.9286 | No change in Phase 02 | → unchanged |

**Note:** Until a new live eval run is completed, the metric improvements for `shares_outstanding` and `net_debt` remain confirmed only at the unit-test level, not at the full-corpus LLM accuracy level.

---

## Unit Test Coverage (Phase 02 specific)

All tests passing at Phase 02 close. Combined count across 6 files: **196 passed, 0 failed**.

| Test file | Tests (Phase 02 scope) | Phase 02 additions |
| --- | --- | --- |
| `test_multipass_extraction.py` | 134 total | `TestIsExplicitNetDebtEvidence` (16), `TestSharesOutstandingMarkers` (3), `TestValidateGateQuarterlyThreshold` (5), `TestNonAUDCurrencyDetection` (7), `TestNonAUDCurrencyNormalisation` (4), `TestDerivedNetDebtFragmentsCoverageGate` (2) |
| `test_extraction_eval_harness.py` | 12 | 0 new; existing 12 pass |
| `test_extraction_eval.py` | 10 | 0 new; existing 10 pass |
| `test_extraction_gold_eval.py` | 14 | `test_real_gold_scorecard_stays_separate_from_synthetic_flow` (1) |
| `test_prose_shares_extraction.py` | 17 | 0 new; existing 17 pass |
| `test_extraction_llm_separation.py` | 9 | 0 new; existing 9 pass |

### Phase 02 test classes summary

| Class | File | Tests | What it guards |
| --- | --- | --- | --- |
| `TestIsExplicitNetDebtEvidence` | multipass | 16 | Derived/movement net debt rows are rejected; explicit point-in-time labels pass |
| `TestSharesOutstandingMarkers` | multipass | 3 | Body-row scan finds `No. '000s` header; absolute counts ≥1M bypass null guard |
| `TestValidateGateQuarterlyThreshold` | multipass | 5 | Quarterly 5B docs accept 1 CF metric; annual/HY still require 3 |
| `TestNonAUDCurrencyDetection` | multipass | 7 | GBP, EUR, CAD, NZD, CNY/CNH/RMB patterns detected correctly |
| `TestNonAUDCurrencyNormalisation` | multipass | 4 | String `"null"` currency treated as AUD; non-AUD warning in structured payload |
| `TestDerivedNetDebtFragmentsCoverageGate` | multipass | 2 | Every `_DERIVED_NET_DEBT_ROW_FRAGMENTS` member is rejected; set is non-empty |

---

## Regression Fixtures Added

Two new synthetic eval fixtures promoted during Phase 02. See [[fixtures/phase-02-new-fixtures]] for full specification.

| Fixture ID | Period type | What it guards |
| --- | --- | --- |
| `quarterly_cashflow_only` | Q | Absent income-statement metrics in Appendix 5B scored as CORRECT (expected null), not MISSING |
| `net_debt_derived_row_abstain` | H | Movement rows do not populate `net_debt`; extractor correctly abstains |

Eval harness fixture count at Phase 02 close: **15 synthetic fixtures, 33+ metric expectations** (harness test confirms fixture discovery).

---

## What Was Fixed (Summary)

1. **Net debt derived-row rejection** (`_DERIVED_NET_DEBT_ROW_FRAGMENTS` + `_is_explicit_net_debt_evidence`): movement, ratio, opening/closing net debt rows are rejected from explicit candidate selection. Prevents fabricated point-in-time net debt from reconciliation tables.

2. **shares_outstanding evidence scan** (all body-row cells, first 3 rows): SEG-style `No. '000s` column label in `row[1]` was missed by the previous `row[0]`-only scan. Fixed by including all cells from the first 3 body rows in `share_surfaces`.

3. **Absolute share count bypass** (values ≥ 1M): LLM-returned share counts that are inherently self-evident (the extraction prompt requires absolute counts) are no longer nulled by the weak-evidence guard.

4. **Quarterly validation gate** (`min_metrics = 1` for `period_type == "Q"`): Appendix 5B filings are structurally cash-flow-only. A single non-null CF metric now passes the gate; annual and HY documents still require ≥ 3.

5. **Non-AUD currency handling**: Extended `_CURRENCY_PATTERNS` to cover 5 additional ASX-relevant currencies; fixed string-`"null"` currency normalisation at Pass 1; surfaced `non_aud_currency:<CODE>` in structured extraction warnings.

---

## What Remains Open (Phase 03 candidates)

| Item | Backlog rank | Why not addressed in Phase 02 |
| --- | --- | --- |
| BHP FY25 current-period revenue column selection | Rank 1 | Requires parser-path investigation across both pymupdf and docling; outside Phase 02 scope |
| BHP FY25 net_debt note/supplementary table extraction | Rank 1 | Requires table-surface investigation; outside Phase 02 scope |
| `shares_outstanding` cross-format hardening | Rank 3 | Phase 02 fixes the two most confident patterns; remaining 50% accuracy gap likely needs live eval to identify residual cases |
| Current-period column selection as a shared selector problem | Rank 4 | Correct fix requires rethinking the `period_col` propagation and retry chain as a unit; deferred to avoid drift during Phase 02 |
| Quarterly validation-gate status inconsistency | Rank 5 | Gate metric threshold fixed in Phase 02; the `extraction_status=failed` vs metric-correct inconsistency is a separate surfacing issue |
| Gold corpus corrections (BHP FY21, MIN H1 FY26) | — | Both require human PDF verification before updating; cannot be automated |

---

## Deliberately Quarantined (Not "Solved")

The following were confirmed as open questions requiring human operator verification, not extractor bugs that can be fixed programmatically:

| Document | Field | Status |
| --- | --- | --- |
| `bhp_a_2021-06-30_difficult` | `expected_trust` in gold corpus | Currently returns `trusted` (all metrics correct) but gold says `abstain`. Gold may be stale. Quarantined until human verifies source PDF. |
| `min_h_2025-12-31` | `net_debt` in gold corpus | Extractor returns `4,878M AUD`; gold expects `null`. If MIN reports net_debt explicitly in the filing, gold must be updated. Quarantined until human verifies. |

No FX conversion was implemented. Non-AUD documents continue to be labelled `ok_low_confidence` with native currency preserved. This is the correct behavior absent an approved FX source.

---

## Contract Note

This report stays inside the backend extraction lane. No Cockpit-side truth adjustment, post-hoc manual overrides, or unsafe derivations were introduced. The evaluation artifacts referenced above are backend-owned. Cockpit displays and orchestrates only.

See [[phase-02-backlog]] for the ranked attack order and root cause analysis behind each fix.
