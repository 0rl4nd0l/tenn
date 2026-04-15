---
type: reference
title: Phase 02 New Regression Fixtures
created: 2026-04-15
tags:
  - extraction
  - fixtures
  - regression
  - phase-02
related:
  - '[[phase-02-backlog]]'
  - '[[phase-01-prototype-report]]'
---

# Phase 02 New Regression Fixtures

Fixtures and unit test cases added or upgraded during Phase 02 Accuracy Hardening. All cases are grounded in failure patterns confirmed in the [[phase-02-backlog]] and the real-gold eval runs from 2026-04-15.

---

## Synthetic Eval Fixtures (`fixtures/extraction_eval/`)

These fixtures test the eval harness logic and are validated against synthetic extraction payloads. No live PDF extraction is run.

### `quarterly_cashflow_only`

**File:** `financial-engine_v2/backend/tests/fixtures/extraction_eval/quarterly_cashflow_only.json`

**Pattern:** Quarterly Appendix 5B document (GRE/EQR pattern). Only `operating_cf` is expected. Income-statement metrics (`revenue`, `ebit`, `np_attributable`) are structurally absent and listed as `expected_nulls`.

**Failure class from backlog:** [[phase-02-backlog]] Rank 5 — quarterly validation-gate inconsistency. Captures the case where an Appendix 5B document passes the quarterly gate (min 1 non-null CF metric) but income-statement metrics are absent not because of an extractor error but because the document type does not contain them.

**What this guards:** Prevents a regression where income-statement null metrics in a quarterly document are incorrectly scored as MISSING instead of CORRECT (expected null).

```json
{
  "fixture_id": "quarterly_cashflow_only",
  "period_type": "Q",
  "period_end": "2024-12-31",
  "currency": "AUD",
  "scale": "thousands",
  "metrics": { "operating_cf": -450000 },
  "expected_nulls": ["revenue", "ebit", "np_attributable"]
}
```

---

### `net_debt_derived_row_abstain`

**File:** `financial-engine_v2/backend/tests/fixtures/extraction_eval/net_debt_derived_row_abstain.json`

**Pattern:** Half-year document where revenue and operating_cf are present and correct, but `net_debt` is expected null because the source document only contains movement/reconciliation rows (e.g., "Increase/(decrease) in net debt"), not an explicit point-in-time balance.

**Failure class from backlog:** [[phase-02-backlog]] Rank 2 — net debt abstain/over-extraction split. Captures the MIN H1 FY26 pattern where the document provides a cash-flow reconciliation of net debt changes but no direct balance row. The `_is_explicit_net_debt_evidence` guard should reject all derived/movement rows, leaving `net_debt: null`.

**What this guards:** Prevents a regression where a movement row ("Increase/(decrease) in net debt") passes `_is_explicit_net_debt_evidence` and incorrectly populates `net_debt` with a change figure rather than the period-end balance.

```json
{
  "fixture_id": "net_debt_derived_row_abstain",
  "period_type": "H",
  "period_end": "2025-06-30",
  "currency": "AUD",
  "scale": "millions",
  "metrics": { "revenue": 3052000, "operating_cf": 880000 },
  "expected_nulls": ["net_debt"]
}
```

---

## Unit Test Cases Added (`test_multipass_extraction.py`)

### `TestIsExplicitNetDebtEvidence` — Phase 02 regression additions

Seven new cases added to cover mining-sector ASX row-label patterns not present in the initial Phase 02 hardening:

| Test | Input | Expected | Reason |
|---|---|---|---|
| `test_rejects_increase_decrease_in_net_debt` | "Increase/(decrease) in net debt" | False | Cash-flow movement, not a balance |
| `test_rejects_decrease_increase_in_net_debt` | "Decrease/(increase) in net debt" | False | Sign-reversed movement variant |
| `test_rejects_net_debt_beginning_of_period` | "Net debt: beginning of period" | False | Reconciliation opening balance |
| `test_rejects_net_debt_beginning_of_year` | "Net debt: beginning of year" | False | Annual report opening balance |
| `test_accepts_net_debt_including_lease_liabilities` | "Net debt including lease liabilities" | True | Explicit point-in-time balance |
| `test_accepts_net_debt_position` | "Net debt position" | True | Period-end balance label |

**Code change:** `_DERIVED_NET_DEBT_ROW_FRAGMENTS` in `multipass_extraction.py` extended with:
- `"net debt: beginning"` — reconciliation opening balance label
- `"/(decrease) in net debt"` — covers "Increase/(decrease) in net debt"
- `"/(increase) in net debt"` — covers "Decrease/(increase) in net debt"

### `TestSharesOutstandingMarkers` — absolute count bypass

New case: `test_absolute_count_bypasses_evidence_check`

Verifies that a value ≥ 1M returned by the LLM bypasses the `has_share_count_evidence` null guard even when the table has no recognisable share-count marker. The extraction prompt instructs the LLM to return the absolute count, so a value this large is self-evidently a share count and cannot be a scaled placeholder.

---

## Gold Corpus — No Changes (Requires PDF Verification)

The following suspected corrections from the backlog were NOT made because they require hand-verification against source PDFs:

| Document | Field | Current gold | Suspected correction | Reason not updated |
|---|---|---|---|---|
| `bhp_a_2021-06-30_difficult` | `expected_trust` | `abstain` | `trusted` | Runtime-hardened eval shows correct metrics, but PDF must confirm before updating gold |
| `min_h_2025-12-31` | `net_debt` | `null` | `4,878M AUD` | Eval extracted 4.878B but gold must be verified against PDF note disclosure |

These entries remain intentionally unchanged until a human operator verifies the source PDFs. See [[phase-02-backlog]] §Gold Corpus Corrections Needed.
