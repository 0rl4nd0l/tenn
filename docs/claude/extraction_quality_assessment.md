# Extraction Quality Assessment

> **Date:** 2026-03-24 (session 3 + live eval run)
> **Branch:** cloud/session-20260319
> **Scope:** Multipass extraction pipeline accuracy against real ASX financial PDFs.
> **Method:** Direct PDF/docling cache inspection + test execution + parallel sub-agent source-truth verification (BHP/RMS/MIN PDFs read directly) + extraction output report analysis + **first live eval run** (`pytest -m live_eval`, Mistral 7B Instruct v0.2).

---

## Executive Verdict

**The pipeline design is sound. First live eval run (2026-03-24) produced 58.3% overall accuracy — well below the 85% threshold. Three root causes identified and one fixed.**

The live eval was run successfully for the first time (`eval_results/eval_2026-03-24T071544Z.json`). All 6 fixtures failed their per-fixture thresholds. Three distinct root causes were identified:
1. **Docling timeouts** on BHP (82-page PDF, hit 300s cap) and EQR (17-page PDF, hit 120s base) → PyMuPDF fallback → table structure lost → poor extraction
2. **JSON parentheses parse failure** — LLM outputs `(5,590)` (accounting notation), causing a JSON parse error on EQR balance_sheet; **fixed** in this session
3. **Wrong model loaded** — llamacpp is serving `model.gguf` (Mistral 7B Instruct v0.2), not the intended `qwen2.5-14b-instruct-q4_k_m.gguf`; accuracy numbers are for an unintended model

The 58.3% is therefore a Mistral 7B baseline with two additional handicaps (timeout + JSON bug). The true accuracy for the intended pipeline (Qwen 2.5 14B, cached Docling, JSON bug fixed) is unknown until re-run.

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

**All 25 asserted metric values across the 6 fixtures are confirmed correct from source documents.**

Sub-agent direct PDF verification (BHP/RMS/MIN, 17 metrics):
- BHP: revenue=60,817M ✓, ebit=25,906M ✓, np_attributable=11,304M ✓
- RMS: all 9 metrics read directly from Appendix 4D / cash flow statement ✓
- MIN: all 5 metrics confirmed from Appendix 4D / cash flow statement ✓

---

## Test Execution Results

```
$ .venv/bin/python -m pytest backend/tests/test_extraction_eval.py -x -q
5 passed, 1 deselected in 0.05s        ← unit mode only (live_eval deselected)

$ .venv/bin/python -m pytest backend/tests/ -x -q --ignore=...test_extraction_eval.py
212 passed in 2.81s       ← +3 new tests for JSON parentheses bug fix
```

### Live Eval Run 1 — 2026-03-24T07:15:44Z

```
$ .venv/bin/python -m pytest -m live_eval backend/tests/test_extraction_eval.py
Duration: 19m 42s
Model: model.gguf (Mistral 7B Instruct v0.2) — NOT the intended Qwen 2.5 14B
Result: FAILED (overall accuracy 0.5833 < threshold 0.85)
```

**Per-fixture results:**

| Fixture | Accuracy | Points | Status |
|---------|----------|--------|--------|
| BHP | 0.7059 | 12/17 | FAIL — Docling timeout (300s), PyMuPDF fallback |
| EQR | 0.5556 | 5/9 | FAIL — Docling timeout (120s), PyMuPDF fallback + JSON parse error |
| GRE | 0.5556 | 5/9 | FAIL |
| MIN | 0.6667 | 4/6 | FAIL |
| RMS | 0.5455 | 6/11 | FAIL |
| SEG | 0.375 | 3/8 | FAIL |

**Per-metric accuracy:**

| Metric | Accuracy |
|--------|----------|
| operating_cf | 0.7143 |
| cash_end | 0.6667 |
| capex | 0.6667 |
| net_debt | 0.625 |
| investing_cf | 0.5714 |
| financing_cf | 0.5714 |
| shares_outstanding | 0.5714 |
| revenue | 0.5 |
| ebit | 0.5 |
| np_attributable | 0.4 |

**Key log warnings from the run:**
```
WARNING docling exceeded 300s on .../BHP/... (falling back to PyMuPDF)
WARNING docling exceeded 120s on .../EQR/... (falling back to PyMuPDF)
WARNING non-AUD currency detected: USD  (BHP: expected; EQR: incorrect — caused by PyMuPDF flat text)
ERROR   Pass 3a retry also failed for balance_sheet: No valid JSON found in llama.cpp response: {"total_debt": (5,590), ...}
```

**Output:** `backend/tests/eval_results/eval_2026-03-24T071544Z.json` (gitignored)

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

### Old Pipeline Output (reports/financial_metrics_bhp_finperf_v13.json)

The `reports/` directory contains extraction output from the **pre-multipass** Docling pipeline. This is the only real-LLM extraction output that exists.

**BHP FY2021-06-30 — old pipeline vs fixture truth:**

| Metric | Fixture (correct) | v13 extracted | Delta | Status |
|--------|------------------|--------------|-------|--------|
| revenue | 60,817,000,000 USD | 56,921,000,000 USD | −6.4% | **WRONG** |
| ebit | 25,906,000,000 USD | 25,515,000,000 USD | −1.5% | **WRONG** |
| net_income (≠ np_attributable) | — | 13,676,000,000 USD | wrong metric | **WRONG METRIC** |
| np_attributable | 11,304,000,000 USD | not extracted | missing | **MISSING** |

Root cause: old pipeline read wrong rows from a multi-column income statement.
- Revenue: extracted 56,921M ("Revenue from continuing operations" subset) vs correct 60,817M (total)
- net_income: extracted "Profit after taxation from Continuing operations" (13,676M) instead of "Profit attributable to BHP shareholders" (11,304M)

This is NOT a multipass pipeline finding — the v13 output pre-dates multipass. But it validates that these errors are real and confirms the fixture values are correct by contrast.

**Cockpit runs (reports/cockpit_update_ticker_financials_*):**
- 375 tickers reviewed in latest full sync (2026-03-24T00:33–01:00)
- All cockpit runs: extraction NOT invoked — pipeline performs document ingestion and classification only
- One failed run: `cockpit_update_ticker_financials_aeeaf28d.json` — PostgreSQL `OperationalError` (name resolution failure), not an extraction bug

### DB Storage (Extraction Runs)

- **`data/financial_engine.db`:** 3 rows in `asx_periodic_financials`, all NAB, all fake (round numbers, UUID 000…001/002/003). Placeholder data only.
- **`data/fe_local.db`:** 59 BHP document records (metadata). 0 rows in `extraction_runs`. 0 rows in `asx_periodic_financials`.
- **Conclusion: No real extraction has ever been committed to any database.** The pipeline has never been run against a real PDF with a real LLM to completion and DB upsert.

---

## Error Taxonomy

| Category | Evidence | Severity | Status |
|----------|---------|---------|--------|
| **Docling timeout — BHP** | BHP is 82 pages; adaptive timeout = 328s → capped at 300s. Always falls back to PyMuPDF flat text. Cache missing. | CRITICAL — affects every eval run until cache is built | Open: cache build in progress |
| **Docling timeout — EQR** | EQR is 17 pages; base 120s timeout exceeded. PyMuPDF fallback causes `ok_low_confidence` (USD detected from flat text). Cache missing. | HIGH — JSON parse error also occurs | Open: cache build in progress |
| **JSON parentheses parse failure** | LLM outputs `(5,590)` (accounting notation) → `ValueError: No valid JSON`. EQR balance_sheet fails on both attempt and retry. | HIGH — hard failure for negative values in accounting notation | **FIXED** — `_parse_json_text` in `llamacpp_runtime.py` now converts `(N)` → `-N` before JSON parse |
| **Wrong model loaded** | `model.gguf` is Mistral 7B Instruct v0.2 (4.1GB), not `qwen2.5-14b-instruct-q4_k_m.gguf` (8.4GB) as intended | HIGH — all accuracy numbers are for wrong model | Open: requires server restart |
| **Old pipeline accuracy failures** | v13 BHP FY2021: revenue −6.4%, ebit −1.5%, wrong metric for np_attributable | HISTORICAL (old pipeline, not multipass) | Historical |
| **MIN Pass 2 misclassification** | Table 0 (4D summary) wins income_statement pool over Table 10 (actual IS) due to equal keyword score + earlier page | MEDIUM (no metric errors for current fixture, but fragile for ebit/np asserted metrics) | Open |
| **highlights table invisible for MIN** | No keywords match Table 0 (Appendix 4D summary) for MIN document | MEDIUM (affects EBIT if ever asserted for MIN) | Open |
| **Scale detection dependency** | Pass 1 LLM must detect scale; override logic is a backstop, not primary | LOW (override exists and is tested) | Open |

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

### CRITICAL: Docling Cache Missing for BHP and EQR

BHP (82 pages) exceeds the 300s DOCLING_TIMEOUT_MAX on every cold run. EQR (17 pages) also exceeded the 120s base timeout. Both need a one-time offline cache build:

```bash
# Run once without timeout cap — cache is written alongside the PDF
python3 -c "
import sys; sys.path.insert(0, 'backend')
import app.services.docling_extract as de
de.DOCLING_TIMEOUT_MAX = 900
de.extract_structured('data/asx/docs/BHP/financial_performance/2021-08-17_preliminary-final-report_37ba70c7-2724-4142-83a9-b55106f78907.pdf')
de.extract_structured('data/asx/docs/EQR/financial_performance/2026-01-21_quarterly-activities-appendix-5b-cash-flow-report-dec-2025_5ea6cd4b-ed13-4220-9ebf-cad83944a4a7.pdf')
"
```

Once the `.docling.json` cache files exist alongside the PDFs, all future eval runs use the cache instantly.

### HIGH: Wrong Model in llamacpp

The server is running `model.gguf` (Mistral 7B Instruct v0.2, 4.1 GB). The intended model is `qwen2.5-14b-instruct-q4_k_m.gguf` (8.4 GB). Accuracy numbers from Run 1 are for Mistral 7B with two additional handicaps. A re-run with the correct model + Docling caches + JSON bug fix will give the first meaningful accuracy numbers for the intended pipeline.

### MEDIUM: MIN Pass 2 Income Statement Misclassification

Table 0 (Appendix 4D highlights-style summary) wins the income_statement pool due to same keyword score + earlier page. This means:
- If `ebit` or `np_attributable` were asserted for MIN, they would be extracted from a 2-row summary table instead of the 36-row full income statement.
- Fix: add `"appendix 4d"` or `"results for announcement"` as a `_STATEMENT_HEADERS["highlights"]` bonus target, AND ensure Table 0 loses the income_statement pool when it should be in highlights. Currently Table 0 is silently misclassified.

---

## MIN Fixture Status Update (COMPLETE)

MIN values confirmed from docling cache and fixture `_source` field updated (committed 68643547):

| Metric | Fixture | Source |
|--------|---------|--------|
| revenue | 3,052,000,000 | Table 10, row "REVENUE = 3,052" |
| operating_cf | 880,000,000 | Table 14, "Net cash from operating activities = 880" |
| investing_cf | -527,000,000 | Table 14, "Net cash used in investing activities = (527)" |
| financing_cf | -126,000,000 | Table 14, "Net cash from financing activities = (126)" |
| shares_outstanding | 196,478,902 | Table 33, "Balance at 31 December 2025 = 196,478,902 (net of treasury)" |

Arithmetic cross-check confirmed: 412 (start) + 880 (ops) − 527 (investing) − 126 (financing) − 1 (FX) = 638 (cash_end). ✓

## Next Required Action

To get the first meaningful accuracy measurement for the **intended pipeline configuration**:
1. Wait for docling cache build to complete for BHP + EQR (background process)
2. Restart llamacpp with `qwen2.5-14b-instruct-q4_k_m.gguf`
3. Run `pytest -m live_eval backend/tests/test_extraction_eval.py`

The JSON parentheses fix (committed this session) will apply automatically.
