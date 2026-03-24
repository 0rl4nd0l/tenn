# Extraction Quality Assessment

> **Date:** 2026-03-24 (session 3 + live eval run)
> **Branch:** cloud/session-20260319
> **Scope:** Multipass extraction pipeline accuracy against real ASX financial PDFs.
> **Method:** Direct PDF/docling cache inspection + test execution + parallel sub-agent source-truth verification (BHP/RMS/MIN PDFs read directly) + extraction output report analysis + **first live eval run** (`pytest -m live_eval`, Mistral 7B Instruct v0.2).

---

## Production Accuracy Standard

The extraction system must achieve high accuracy **reproducibly across thousands of documents** from different companies and sectors. This is a core design principle, not a stretch goal.

- **Generalization over memorization:** Prompt constraints must handle diverse formats (Appendix 4D, 4E, 5B, full IFRS annual reports). Do not encode company-specific patterns that break on unseen documents.
- **Source-verified fixtures only:** Fixture expected values must be verified from source PDFs. Never adjust fixture values to match model output — if the model disagrees with the fixture, the model is wrong or the extraction logic needs fixing.
- **Regression gate vs. production validation:** The 6-fixture eval is a regression gate that catches prompt/code regressions. It is not a quality certificate. Production accuracy must be validated against a broader, continuously expanding document set.
- **Model consensus is not correctness:** Agreement between two models (e.g., Claude and Qwen both returning the same value) does not prove the value is correct. Both can be systematically wrong if the prompt steers them the same way. Ground truth comes from the source PDF, not from model agreement.

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

### Live Eval — Three Runs Summary

All three runs used `model.gguf` (Mistral 7B Instruct v0.2, not the intended Qwen 2.5 14B).

| Run | Timestamp | Duration | Overall | BHP | EQR | GRE | MIN | RMS | SEG | Notes |
|-----|-----------|----------|---------|-----|-----|-----|-----|-----|-----|-------|
| 1 | 071544Z | 19m 42s | 58.3% | 70.6% | 55.6% | 55.6% | 66.7% | 54.5% | 37.5% | No Docling cache, JSON bug, no api-key req |
| 2 | 073606Z | ~18s | 48.3% | 82.4% | 55.6% | 55.6% | 16.7% | 18.2% | 25.0% | Docling cache, JSON fix, BUT 401 (no client key) |
| 3 | 074305Z | 5m 48s | 45.0% | 23.5% | 55.6% | 55.6% | 66.7% | 54.5% | 37.5% | Docling cache, JSON fix, api-key correct — **canonical Mistral 7B run** |

**Key findings from cross-run comparison:**

1. **EQR, GRE constant at 55.6% across all runs** — Docling cache and JSON fix had no effect on these quarterly fixtures. The extraction result is determined by the LLM, not by document parsing quality for these simple cash-flow-only documents.

2. **MIN, RMS, SEG constant at 66.7/54.5/37.5% between Run 1 and Run 3** — These already had Docling caches in Run 1 (no impact from cache build). Dropping to 16.7/18.2/25.0 in Run 2 confirms that was caused by 401 errors, not Docling.

3. **~~BHP fixture design issue — CRITICAL~~** (RESOLVED): BHP `expected_nulls` included 7 unverified metrics. These have now been hand-verified from the docling cache and added to `metrics` with correct values. `expected_nulls` cleared. Future runs will correctly reward extraction of CF/BS values instead of penalizing it.

4. **JSON fix impact on EQR**: The JSON parentheses fix should have helped EQR's balance_sheet extraction in Run 3. EQR stayed at 55.6% across all runs — suggesting either the balance_sheet data was never driving the score, or the EQR document structure produces the same result regardless.

**Run 3 per-fixture details:**

| Fixture | Accuracy | Status |
|---------|----------|--------|
| BHP | 23.5% | FAIL — fixture design issue (see above) |
| EQR | 55.6% | FAIL |
| GRE | 55.6% | FAIL |
| MIN | 66.7% | FAIL |
| RMS | 54.5% | FAIL |
| SEG | 37.5% | FAIL |

**Run 3 per-metric accuracy:**

| Metric | Accuracy | Notes |
|--------|----------|-------|
| revenue | 0.667 | 3 fixtures — improved from 0.5 in Run 1 |
| capex | 0.667 | |
| ebit | 0.5 | |
| np_attributable | 0.6 | improved from 0.4 |
| shares_outstanding | 0.571 | |
| operating_cf | 0.429 | degraded from 0.714 — likely BHP's null penalization |
| investing_cf | 0.286 | degraded from 0.571 |
| financing_cf | 0.286 | degraded from 0.571 |
| cash_end | 0.333 | degraded from 0.667 |
| net_debt | 0.375 | degraded from 0.625 |

The CF metric degradation from Run 1 → Run 3 is almost entirely explained by BHP: Run 1 used PyMuPDF (null for CF), Run 3 uses Docling (extracts CF values) → BHP expected_null checks fail for all CF metrics.

**Run 1 key log warnings:**
```
WARNING docling exceeded 300s on .../BHP/... (falling back to PyMuPDF)
WARNING docling exceeded 120s on .../EQR/... (falling back to PyMuPDF)
WARNING non-AUD currency detected: USD  (BHP: expected; EQR: incorrect — PyMuPDF flat text)
ERROR   Pass 3a retry also failed for balance_sheet: No valid JSON found in llama.cpp response: {"total_debt": (5,590), ...}
```

**Output files (gitignored):**
- `backend/tests/eval_results/eval_2026-03-24T071544Z.json` (Run 1)
- `backend/tests/eval_results/eval_2026-03-24T073606Z.json` (Run 2, 401 errors)
- `backend/tests/eval_results/eval_2026-03-24T074305Z.json` (Run 3, canonical)

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
| **Docling timeout — BHP** | BHP is 82 pages; adaptive timeout = 328s → capped at 300s. Always falls back to PyMuPDF flat text. Cache missing on Run 1. | CRITICAL — but **RESOLVED**: cache built offline in 155s (98 tables, 82 pages). All future runs use cache. | Fixed |
| **Docling timeout — EQR** | EQR is 17 pages; base 120s timeout exceeded (likely cold model load). PyMuPDF fallback causes `ok_low_confidence` (USD detected from flat text). Cache missing on Run 1. | HIGH — **RESOLVED**: cache built offline in 18s (12 tables, 17 pages). EQR now runs with proper table structure. | Fixed |
| **JSON parentheses parse failure** | LLM outputs `(5,590)` (accounting notation) → `ValueError: No valid JSON`. EQR balance_sheet fails on both attempt and retry. | HIGH — hard failure for negative values in accounting notation | **FIXED** (d9241dee) — `_parse_json_text` in `llamacpp_runtime.py` now converts `(N)` → `-N` before JSON parse; 3 tests added |
| **BHP fixture expected_nulls design flaw** | BHP `expected_nulls` marked CF/BS metrics as "expected null" because they were unverified — not because they're absent. Docling surfaces 98 real tables; pipeline correctly extracts CF metrics; eval penalized correct extraction. | HIGH — inflated BHP accuracy when pipeline returned all-null (82.4%) vs correct extraction (23.5%) | **FIXED** — all 10 metrics now hand-verified from docling cache (tables 4, 8, 12, 45, 46, 57, 76); `expected_nulls` cleared |
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
| operating_cf | BHP, RMS, MIN, SEG, GRE, EQR | All confirmed |
| investing_cf | BHP, RMS, MIN, SEG, GRE, EQR | All confirmed |
| financing_cf | BHP, RMS, MIN, SEG, GRE, EQR | All confirmed |
| cash_end | BHP, RMS, SEG, GRE, EQR | All confirmed |
| capex | BHP, RMS | Both confirmed (BHP: PP&E + exploration; RMS: PP&E only) |
| net_debt | BHP | Confirmed from highlights + net debt bridge |
| shares_outstanding | BHP, RMS, MIN | All confirmed (BHP: weighted basic average, dual-listed) |
| expected_nulls | 5 fixtures (GRE, EQR, SEG, RMS, MIN) | Structurally tested; BHP cleared |

**All 32 fixture assertions are backed by source-document evidence. None are model-estimated.** (Was 25 before BHP redesign.)

---

## Remaining Gaps

### ~~CRITICAL: Docling Cache Missing for BHP and EQR~~ — RESOLVED

BHP: cache built offline in 155s (98 tables). EQR: cache built offline in 18s (12 tables). Both caches written at `data/asx/docs/{BHP,EQR}/financial_performance/*.pdf.docling.json`, version=2.75.0. All future eval runs hit cache instantly.

### HIGH: Wrong Model in llamacpp

The server is running `model.gguf` (Mistral 7B Instruct v0.2, 4.1 GB). The intended model is `qwen2.5-14b-instruct-q4_k_m.gguf` (8.4 GB). Run 3 (45.0% overall) is the canonical Mistral 7B baseline — Docling caches built, JSON fix applied, correct API key. Runs with the correct Qwen 2.5 14B model will give the first meaningful accuracy for the intended pipeline.

Also: **llamacpp now requires `Authorization: Bearer local-openai-key`** (started with `--api-key local-openai-key`). Run `pytest -m live_eval` with `LLM_API_KEY=local-openai-key` prefixed, or add that export to the shell environment.

### ~~HIGH: BHP Fixture Expected_Nulls Design Flaw~~ — RESOLVED

All 7 previously-unverified metrics (operating_cf, investing_cf, financing_cf, cash_end, capex, net_debt, shares_outstanding) have been hand-verified from the BHP docling cache (98 tables). Values sourced from:
- Cash flow statement (Table 46): operating_cf=27,234M, investing_cf=(7,845M), financing_cf=(17,922M), cash_end=15,246M
- Highlights (Table 4): capex=7,120M, net_debt=4,121M — cross-checked against net debt bridge (Table 8) and balance sheet (Table 45)
- EPS notes (Table 12/57): shares_outstanding=5,057M (weighted basic average, dual-listed)

`expected_nulls` cleared to empty list. BHP now asserts all 10 metrics with 1% tolerance. BHP fixture metric count: 10 asserted values + 1 period_end = 11 data points (was 3 + 7 null-checks + 1 period_end = 11).

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

## Next Required Actions

To get the first meaningful accuracy measurement for the **intended pipeline configuration**:

1. ~~**[Required]** Hand-verify BHP CF/BS metrics and fix the `expected_nulls` design flaw~~ — **DONE**. All 10 BHP metrics now hand-verified from docling cache.
2. **[Required]** Restart llamacpp with `qwen2.5-14b-instruct-q4_k_m.gguf` — currently serving Mistral 7B.
3. **[Required]** Run eval with correct env: `LLM_API_KEY=local-openai-key pytest -m live_eval backend/tests/test_extraction_eval.py`

The JSON parentheses fix, Docling caches, and BHP fixture redesign are all in place.
