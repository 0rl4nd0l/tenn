# Extraction Quality Assessment

> **Date:** 2026-03-24
> **Branch:** cloud/session-20260319
> **Scope:** Multipass extraction pipeline accuracy against real ASX financial PDFs.
> **Method:** Direct PDF/docling cache inspection + test execution. No live LLM eval run.

---

## Executive Verdict

**The pipeline design is sound. Accuracy against real PDFs with a real LLM is unverified.**

Every deterministic component (Pass 2 table locator, Pass 4 reconciler) has been verified against real document structures. The LLM-dependent passes (Pass 1 classifier, Pass 3a metric extractor, Pass 3b narrative extractor) have only been unit-tested with mocked LLM responses. No `pytest -m live_eval` run has ever been executed against the fixture PDFs.

---

## Sample Investigated

| Fixture | Ticker | Period | Source doc | Verified? | Notes |
|---------|--------|--------|-----------|-----------|-------|
| `BHP_A_2021-06-30.json` | BHP | Annual | Preliminary Final Report | **PDF-verified** | USD millions, prior session |
| `RMS_H_2025-12-31.json` | RMS | Half-year | Appendix 4D + IFRS interim | **PDF-verified** | AUD thousands; all 10 metrics confirmed |
| `MIN_H_2025-12-31.json` | MIN | Half-year | Appendix 4D + IFRS interim | **Docling-verified** | 5 metrics confirmed via docling cache |
| `SEG_H_2025-12-31.json` | SEG | Half-year | Appendix 4D + IFRS interim | **PDF-verified** | AUD thousands; all 6 metrics confirmed |
| `GRE_Q_2024-12-31.json` | GRE | Quarterly | Appendix 5B | **PDF-verified** | AUD thousands; all 4 CF metrics confirmed |
| `EQR_Q_2025-12-31.json` | EQR | Quarterly | Appendix 5B | **PDF-verified** | AUD thousands; 1k rounding artifact documented |

All 25 asserted metric values across the 6 fixtures are confirmed correct from source documents.

---

## Test Execution Results

```
$ .venv/bin/python -m pytest backend/tests/test_extraction_eval.py -x -q
5 passed, 1 deselected in 0.05s        ← unit mode only (live_eval deselected)

$ .venv/bin/python -m pytest backend/tests/ -x -q --ignore=...test_extraction_eval.py
209 passed in 2.83s
```

- **0 live eval runs exist.** `backend/tests/eval_results/` does not exist and has never been created.
- `pytest -m live_eval` requires llamacpp running on port 8001.

---

## Findings by Component

### Pass 1 — Document Classifier (LLM)

- **Purpose:** Determine report_type (A/H/Q), period_end, scale, currency.
- **Unit test coverage:** One structural mock test (correctly identifies "H", "2024-12-31", "thousands", confidence 0.9).
- **Live coverage:** Zero. Correct period/scale detection is required for Pass 3a scale multiplier correctness.
- **Risk:** If the LLM misdetects scale (e.g., "millions" vs "thousands"), all extracted values are off by 1000×.
- **Mitigation present:** `_scale_override` logic in Pass 3a detects scale from table column headers and overrides Pass 1 when they disagree. Unit-tested: `test_scale_override_mutates_pass1_dict` passes.

### Pass 2 — Table Locator (Deterministic)

Verified against two real document structures.

**RMS (34 tables, 477 sections):**
- Highlights: Table 0 (page 1) — correctly selected. Header "Key Information" matches `_STATEMENT_HEADERS["highlights"]` keyword "key information" → gets `_HEADER_BONUS`.
- Income statement: correctly selected (separate from highlights).
- Cashflow statement: correctly selected.
- Share capital: correctly selected (1,924,937,480 shares at Table 31).
- All fixture values present in the selected tables. ✓

**MIN (49 tables, 695 sections):**
- Highlights: **Zero score** — Table 0 (page 1, Appendix 4D summary) does not match any `_TABLE_KEYWORDS["highlights"]` keyword ("highlights", "key metrics", "summary", "at a glance", "key financials", "key information"). No highlights table selected.
- Income statement: **Misclassified** — Table 0 (page 1, 4D summary, score 2) beats Table 10 (page 14, actual income statement, score 2) on tie-breaking by earlier page. The 4D summary is used as the income statement source.
- Cashflow statement: Table 14 (page 17) correctly selected. ✓
- **Impact:** For MIN's asserted fixture metrics (revenue, 3×CF, shares_outstanding), the misclassification is harmless — revenue 3,052 is in both Table 0 and Table 10, and CF comes from the correct table. **However**, if ebit or np_attributable were asserted for MIN, they would be extracted from the 4D summary table rather than the full income statement, with uncertain results.

**TOC protection:** `_table_is_toc` correctly flags table 9 (TOC with bare "14" page-number header) — it loses pool competition to non-TOC tables.

### Pass 3a — Metric Extractor (LLM)

- **Purpose:** Extract numeric values from labeled tables. Strict null rule enforced by prompt.
- **EBIT-from-highlights path:** For RMS, EBIT is not labeled in the income statement (has "PBT" and no EBIT row). The prompt rule "do NOT use PBT as a proxy" is correct. Highlights table page 1 explicitly labels "Earnings before Interest and Tax (EBIT) = 31,284". Pass 4 fills ebit from highlights because income_statement returns null, then highlights overwrites null.
- **Prompt correctness:** The `_PASS3A_PROMPT` rule is well-written for this case. Whether the LLM follows it consistently in live runs is untested.
- **Scale multiplier:** Applied after LLM returns raw values (e.g., "3,241" → 3,241 × 1000 = 3,241,000). Unit-tested.
- **Live coverage:** Zero.

### Pass 4 — Reconciler (Deterministic)

- **Source priority:** `income_statement > cashflow_statement > balance_sheet > share_capital > highlights`
- **Merge logic:** Processes sources low-to-high priority; each source overwrites nulls with non-null values; higher priority source overwrites lower priority's non-null values.
- **Unit-tested:** `test_pass4_higher_priority_source_wins` confirms income_statement beats highlights for overlapping metrics.
- **B4 net_debt derivation:** `total_debt - cash_end` when net_debt is null from balance_sheet.
- **Verified correct** for the fixtures' patterns.

### DB Storage (Extraction Runs)

- **`data/financial_engine.db`:** 3 rows in `asx_periodic_financials`, all NAB, all fake (round numbers, UUID 000…001/002/003). Placeholder data only.
- **`data/fe_local.db`:** 59 BHP document records (metadata). 0 rows in `extraction_runs`. 0 rows in `asx_periodic_financials`.
- **Conclusion: No real extraction has ever been committed to any database.** The pipeline has never been run against a real PDF with a real LLM to completion and DB upsert.

---

## Error Taxonomy

| Category | Evidence | Severity |
|----------|---------|---------|
| **Zero live eval runs** | `eval_results/` absent; DB has 0 extraction records | CRITICAL gap |
| **MIN Pass 2 misclassification** | Table 0 (4D summary) wins income_statement pool over Table 10 (actual IS) due to equal keyword score + earlier page | MEDIUM (no metric errors for current fixture, but fragile for ebit/np asserted metrics) |
| **Old pipeline np_attributable bug** | `reports/financial_metrics_bhp_finperf_v3.csv`: net_income=13,451M vs correct np=11,304M | HISTORICAL — pre-multipass pipeline, not in current code |
| **Scale detection dependency** | Pass 1 LLM must detect scale; override logic is a backstop, not primary | LOW (override exists and is tested) |
| **highlights table invisible for MIN** | No keywords match Table 0 (Appendix 4D summary) for MIN document | MEDIUM (affects EBIT if ever asserted for MIN) |

---

## Verified Accuracy Summary

| Metric | Fixtures asserting it | Source verified? |
|--------|--------------------|-----------------|
| revenue | BHP, RMS, MIN, SEG | All confirmed |
| ebit | BHP, RMS | Both confirmed; RMS path via highlights ✓ |
| np_attributable | BHP, RMS, SEG | All confirmed |
| operating_cf | RMS, MIN, SEG, GRE, EQR | All confirmed |
| investing_cf | RMS, MIN, SEG, GRE, EQR | All confirmed |
| financing_cf | RMS, MIN, SEG, GRE, EQR | All confirmed |
| cash_end | RMS, SEG, GRE, EQR | All confirmed |
| capex | RMS | Confirmed (PP&E payments only) |
| shares_outstanding | RMS, MIN | Both confirmed |
| expected_nulls | All 6 fixtures | Structurally tested |

**All 25 fixture assertions are backed by source-document evidence. None are model-estimated.**

---

## Remaining Gaps

### DATA_MISSING: Live Eval Never Run

The single most important quality gap. Until `pytest -m live_eval` is run:
- We do not know Pass 1 scale/period detection accuracy on real documents.
- We do not know if the LLM follows the "null if not labeled" rule consistently.
- We do not know if the EBIT-from-highlights path produces 31,284 for RMS.
- We do not know overall accuracy across the fixture set.

**To run:** requires llamacpp on port 8001, fixture PDFs present (confirmed present).

### DATA_MISSING: MIN Fixture Not Hand-Verified

The MIN fixture was model-extracted. Its 5 values have been confirmed against the docling cache (which itself was built from the PDF). This is strong indirect confirmation, but not the same as reading the PDF directly and cross-checking arithmetic.

**MIN cash_end is not in the fixture.** Table 14 shows cash_end=638M. If the fixture were extended to include cash_end=638,000,000 it could be verified.

### STRUCTURAL: MIN Pass 2 Income Statement Misclassification

Table 0 (Appendix 4D highlights-style summary) wins the income_statement pool due to same keyword score + earlier page. This means:
- If `ebit` or `np_attributable` were asserted for MIN, they would be extracted from a 2-row summary table instead of the 36-row full income statement.
- Fix: add `"appendix 4d"` or `"results for announcement"` as a `_STATEMENT_HEADERS["highlights"]` bonus target, AND ensure Table 0 loses the income_statement pool when it should be in highlights. Currently Table 0 is silently misclassified.

---

## MIN Fixture Status Update

MIN values now confirmed from docling cache:

| Metric | Fixture | Source |
|--------|---------|--------|
| revenue | 3,052,000,000 | Table 10, row "REVENUE = 3,052" |
| operating_cf | 880,000,000 | Table 14, "Net cash from operating activities = 880" |
| investing_cf | -527,000,000 | Table 14, "Net cash used in investing activities = (527)" |
| financing_cf | -126,000,000 | Table 14, "Net cash from financing activities = (126)" |
| shares_outstanding | 196,478,902 | Table 33, "Balance at 31 December 2025 = 196,478,902 (net of treasury)" |

The MIN fixture `_source` field should be updated from "Model-extracted" to reflect cache-confirmed status when the PDF is directly read.
