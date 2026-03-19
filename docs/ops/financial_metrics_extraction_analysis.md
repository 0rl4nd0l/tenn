# Financial Metrics Extraction — Holes and Inconsistencies Analysis

Analysis of period parsing, canonical vs context classification, tests, data quality, and downstream consumers. **No code was modified**; recommendations only.

---

## 2026-03-04 Implementation Status (Follow-up)

The recommendations in this analysis are now partially implemented in `scripts/extract_financial_metrics.py` and `scripts/query_financial_metrics.py`.

Implemented:
- Added explicit canonical provenance tiering:
  - `canonical_tier = strict | table_promoted`
  - `canonical_promotion_reason`
  - `promoted_to_canonical_tier` (on originating context rows)
- Added controlled table-context promotion for high-quality reconciliation rows for:
  - `free_cash_flow`, `operating_cash_flow`, `capex`, `net_debt`, `total_debt`
- Added ranking preference for `strict` over `table_promoted` during canonical conflict resolution and primary row selection.
- Added query-time tier filter:
  - `--canonical-tier strict|table_promoted`
- Added tests for promotion behavior and component-row rejection.

Additional hardening applied after this analysis:
- Synthetic Docling header rows (`0 1 2` style) are demoted to context (`context_reason = synthetic_table_header`).
- Document-level quarantine rules are enabled by default to prevent known non-representative subsidiary docs from polluting parent entities (for example 29M EMR/Golden Grove docs).

Current open risks (still monitor):
- Period/entity attribution can still be ambiguous in multi-entity tables when dates and entity labels co-occur in dense blocks.
- Users must distinguish filing cadence (`reporting_cadence`) from metric scope (`period_scope`) to avoid mixing flow and stock interpretations.

---

## 1. Period parsing (recent fix)

### 1.1 `_extract_explicit_date_labels` — DD-MON-YY and 2-digit year

**Location:** `scripts/extract_financial_metrics.py` lines 1013–1043.

- **Regex:** `(?:AS\s+AT\s+)?(\d{1,2})[-/]([A-Za-z]{3,4})[-/](\d{2,4})` correctly handles "AS AT DD-MON-YY", "DD-MON-YY", and 4-digit year.
- **2-digit year:** `year_val <= 50` → 20xx, `> 50` → 19xx. Boundaries: 00→2000, 50→2050, 51→1951, 99→1999. Implemented as intended.
- **Invalid day:** `date(full_year, month_num, day)` is inside `try/except ValueError: continue` (lines 1033–1036), so invalid dates (e.g. 31-Feb) are skipped without raising.
- **Invalid month:** `month_num is None` leads to `continue`; unknown tokens are skipped.
- **Order of patterns:** Results are built from `DATE_PERIOD_RE` (4-digit only), then `loose_re`, `split_seq_re`, then `as_at_dd_mon_re`. So **order of dates in the returned list follows finditer order**, not necessarily left-to-right in the document.

**Holes / edge cases:**

| Issue | Location | Detail |
|-------|----------|--------|
| **Mixed formats, order** | 967–1043 | If header is e.g. "AS AT 30-JUN-25  31 December 2024", `DATE_PERIOD_RE` finds "31 December 2024" first, then `as_at_dd_mon_re` finds 30-JUN-25. Output order can be ["31 December 2024", "30 June 2025"] while visually the first column is 30 June 2025. Column mapping in `_date_for_col` can then assign the later column to the earlier date. |
| **Single date, two columns** | 2677–2694 | If header has the same date twice (e.g. "30 June 2025  30 June 2025"), deduplication in `_extract_explicit_date_labels` yields one label. `_date_for_col` with `ncols=2, ndates=1` then returns "" for both columns (idx and idx2 both out of range). Both columns fall back to base_period/context; if that’s wrong or empty, both can get the same or wrong period. |
| **3+ columns** | 2681–2693 | With e.g. 3 columns and 2 date labels, `idx = col_order_idx - (ncols - ndates)` gives col 0 → idx -1 (no date), cols 1 and 2 get the two dates. That matches a layout with one non-date column then two period columns; if the layout is different (e.g. two dates then one variance column), mapping can be wrong. |

### 1.2 Interaction with `_resolve_table_period_for_column`

**Location:** `scripts/extract_financial_metrics.py` lines 2655–2810.

- **base_period** comes from `columns[cidx].get("period")` or `region.get("period_hint")`. Column `period` is set in **infer_column_metadata** (line 715) using **extract_period_labels** (and infer_header_date_from_mixed_text). **extract_period_labels** uses `DATE_PERIOD_RE` (4-digit year only) and does **not** use `_extract_explicit_date_labels`. So for a header with only "30-JUN-25", column period is empty; we rely on **table_header_text** in `_resolve_table_period_for_column`.
- **header_dates** = `_extract_explicit_date_labels(table_header_text)` — so the full header string gets DD-MON-YY parsing; column-to-period mapping then uses `_date_for_col(header_dates)`.
- **context_dates** = `_extract_explicit_date_labels(block_context)` — block context also gets the new parsing.
- **Preference:** If `hdr_period` is set, it overwrites a non-explicit base period (lines 2703–2714). So table_header_text (and thus the new regex) wins when it produces a date.

**Inconsistency:** Column-level `period` in `infer_column_metadata` (lines 684–715) never uses `_extract_explicit_date_labels`, so per-column "period" can be empty for DD-MON-YY-only headers. Period resolution still works because `table_header_text` is passed and used for header_dates. Recommendation: document this or optionally use `_extract_explicit_date_labels` in infer_column_metadata for per-column text so column period is populated for prospectus-style headers.

---

## 2. Canonical vs context classification

### 2.1 Flow from bbox rows → statement_period_end → classify

- **Where statement_period_end is set (table path):** Lines 2597–2621. `statement_period_value` = `_resolve_table_period_for_column(..., table_header_text=region_header_text)`. Then `statement_period_end, _ = normalize_period_for_db(statement_period_value or period_value, doc_date=...)`. So it always comes from the resolved period (header_dates / context_dates / base_period).
- **missing_statement_period_end:** Lines 3016–3021. After all context checks (pro_forma, ambiguous row, reconciliation, etc.) and before scope/confidence checks, `statement_period_end` is read. If empty, row gets `context_reason = "missing_statement_period_end"` and is appended to **context_rows**, not rejected. So rows with no period are kept as context with a clear reason.

### 2.2 Paths where period can be set from narrative/block but not table_header_text

- **base_period** = `columns[cidx].get("period")` or `region.get("period_hint")`. `region.period_hint` comes from **infer_region_period_hint** (line 1886), which scans page lines and uses **extract_period_labels** (again 4-digit only). So region period_hint does **not** see DD-MON-YY in block text.
- In `_resolve_table_period_for_column`, if `header_dates` yields nothing, we use `context_dates` (block_context). So period **can** come from block context when table_header_text has no parseable dates; block context is also run through `_extract_explicit_date_labels`, so DD-MON-YY in block_context **is** used there.
- If both header_dates and context_dates are empty, we keep base_period (from column or region). So period can be set from narrative/region (via period_hint / extract_period_labels) when neither header nor block has explicit dates; in that case DD-MON-YY in block would still not be used for region period_hint (only for context_dates when we're in _resolve_table_period_for_column).

### 2.3 context_reason and rows with period still landing in context

- Rows **with** a non-empty `statement_period_end` can still be classified as context for many reasons: pro_forma_context, reconciliation_context, parent_entity_context, narrative_row_label, ambiguous_row_label, low_canonical_confidence, canonical_conflict_same_period, balance_sheet_identity_guard, etc. So having a period does not imply canonical.
- **Consistency:** The only path that sets `context_reason = "missing_statement_period_end"` is the one where `statement_period_end` is empty (3018–3020). All other context_reason values are set earlier in the loop. No double-assignment of context_reason observed.

---

## 3. Tests

### 3.1 `test_extract_explicit_date_labels_as_at_dd_mon_yy_prospectus`

**Location:** `scripts/test_pdf_financial_tools.py` lines 418–428.

- **Covered:** Prospectus-style "AS AT 30-JUN-25", "30-JUN-24"; without "AS AT" ("30-JUN-25 and 31-DEC-24"); output "30 June 2025", "30 June 2024", "31 December 2024".
- **Not covered:**
  - **2-digit year boundaries:** 00 (2000), 50 (2050), 51 (1951), 99 (1999).
  - **4-digit year:** e.g. "AS AT 30-JUN-2025" (year_val >= 100 → full_year = year_val).
  - **Invalid month:** e.g. "30-XYZ-25" should not appear in output.
  - **Invalid day:** e.g. "31-FEB-25" should not appear (or should be skipped).

**Suggested tests (add to same test class):**

```python
def test_extract_explicit_date_labels_2digit_year_boundaries(self):
    self.assertIn("1 January 2000", EXTRACT._extract_explicit_date_labels("AS AT 01-JAN-00"))
    self.assertIn("30 June 2050", EXTRACT._extract_explicit_date_labels("AS AT 30-JUN-50"))
    self.assertIn("31 December 1951", EXTRACT._extract_explicit_date_labels("31-DEC-51"))
    self.assertIn("1 July 1999", EXTRACT._extract_explicit_date_labels("01-JUL-99"))

def test_extract_explicit_date_labels_four_digit_year(self):
    labels = EXTRACT._extract_explicit_date_labels("AS AT 30-JUN-2025")
    self.assertIn("30 June 2025", labels)

def test_extract_explicit_date_labels_invalid_month_skipped(self):
    labels = EXTRACT._extract_explicit_date_labels("30-XYZ-25 30-JUN-25")
    self.assertNotIn("30 XYZ 2025", labels)
    self.assertIn("30 June 2025", labels)

def test_extract_explicit_date_labels_invalid_day_skipped(self):
    labels = EXTRACT._extract_explicit_date_labels("31-FEB-25")
    self.assertEqual(labels, [])
```

### 3.2 Column mapping tests

- **Missing:** No test that two (or more) explicit dates in a single header string map to the correct columns via `_resolve_table_period_for_column`. For example: header "AS AT 30-JUN-25  AS AT 30-JUN-24", col_idx 0 → "30 June 2025", col_idx 1 → "30 June 2024".
- **Suggested:** Add a test that builds `header_dates` from such a string and calls `_resolve_table_period_for_column` for col_idx 0 and 1 with `ordered_col_indices=[0, 1]` and asserts the returned period strings.

---

## 4. Data quality / invariants

### 4.1 Prospectus tables and subsidiary names (Peak View, Deep Dykes)

- **Risk:** In a block that contains both "PEAK VIEW EXPLORATION PTY LTD AS AT 30-JUN-25" and "DEEP DYKES ... AS AT 30-JUN-24", `_extract_explicit_date_labels` returns all dates from the whole block. When this block text is used as **table_header_text** or **block_context**, dates are not tied to entity names. So we can get ["30 June 2025", "30 June 2024"] with no indication which date belongs to which subsidiary; column mapping then relies on column order. If the layout has subsidiary A’s column first and B’s second, mapping is correct only if the header order matches.
- **Recommendation:** No code change in this analysis; consider documenting that multi-entity blocks are ambiguous and that period-to-entity association is by position only. Optional: add a data-quality check or flag when the same block contains multiple entity-like names and multiple dates.

### 4.2 `normalize_period_for_db` with "30 June 2025" style

- **Location:** `scripts/extract_financial_metrics.py` lines 1297–1330.
- **Flow:** `explicit = _parse_date_label(period) or _parse_quarter_end_label(period)`. `_parse_date_label` (903–941) first uses `DATE_PERIOD_RE` on the string (e.g. "30 June 2025"); that regex is `\d{1,2}\s+MONTH_TOKEN\s+20\d{2}`, which matches. So we get a date and return `explicit.isoformat()`. So **normalize_period_for_db correctly handles the "30 June 2025" style** produced by `_extract_explicit_date_labels`.

---

## 5. Other scripts / callers

| Consumer | Use of statement_period_end / context | Assumption / risk |
|----------|----------------------------------------|-------------------|
| **reconcile_user_table_vs_evidence.py** | Lines 99, 155: `period = (row.get("statement_period_end") or "").strip()`; key `(metric, period)`. Line 233: writes back `statement_period_end`. | Expects non-empty period for comparison; empty period skips row (lines 170–174). No format assumption beyond string. |
| **section_capture_layer.py** | Lines 424, 633, 659, 684, 704, 755–756, 779, 797, 1092, 1384, 1391: grouping, merging, required columns. | Uses `(file, statement_period_end)` as key; expects string, often ISO date. Empty period can create a single bucket for all empty-period rows. |
| **validation_quality_cycle.py** | Lines 40, 46, 50, 65: period column candidates include `statement_period_end`. | Used to find a period column; no strict format. |
| **validation_gates.py** | Lines 40, 87, 148, 197–198: period from row, key grouping. | Same as above. |
| **run_ticker_expansion_batch.py** | Line 212: counts rows with blank `statement_period_end` (or period_end). | Treats blank as "missing"; no format assumption. |
| **extract_financial_metrics.py** (summary/export) | Lines 4314–4319: default output paths for context CSV/JSON. | Context JSON includes canonical and context rows; context rows can have `statement_period_end` empty and `context_reason = "missing_statement_period_end"`. Downstream that expects every row to have ISO date will need to handle empty or non-ISO. |

**Recommendation:** Document that `statement_period_end` may be empty for context rows and that when present it should be ISO `YYYY-MM-DD` for canonical and for normalized context. Callers that key on `(file, statement_period_end)` should treat empty as a distinct key or filter.

---

## 6. Summary of concrete recommendations

1. **Period parsing:** Add tests for 2-digit year boundaries (00, 50, 51, 99), 4-digit year, invalid month, invalid day; and a test for 2-date header → 2 columns getting correct periods in `_resolve_table_period_for_column`.
2. **Column mapping:** Consider documenting or improving date order when multiple patterns match (e.g. prefer left-to-right order in text for header_dates when mixing formats).
3. **Duplicate dates in header:** Document that when the same date appears in two columns, both columns may get no date from `_date_for_col` and fall back to base_period/context.
4. **infer_column_metadata:** Optionally use `_extract_explicit_date_labels` for per-column header text so column period is set for DD-MON-YY-only headers.
5. **Prospectus / multi-entity:** Document that period–entity association in multi-entity blocks is by position only; consider a quality flag for multiple entity-like names + multiple dates in one block.
6. **Downstream:** Document that `statement_period_end` can be empty and that canonical/callers expect ISO date when present; handle empty in reconciliation and section_capture_layer.

---

*Analysis completed without modifying any code; file paths and line numbers refer to the current tree.*
