# Canonical metric row — validation spec

Used by the PDF financial metrics pipeline (`scripts/extract_financial_metrics.py`). Enforce these rules in a validator without changing the extraction architecture.

## Field spec (from `write_csv` and SQLite)

| Field | Type | Required | Validation |
|-------|------|----------|------------|
| file | string | yes | non-empty |
| line_no | int | no | ≥ 0 |
| metric | string | yes | non-empty; known metric name preferred |
| metric_base | string | no | |
| metric_variant | string | no | |
| metric_alias | string | no | |
| value_type | string | yes | one of: `amount`, `percent`, `text` |
| raw_value | string | no | |
| value | number | when amount/percent | finite; optional |value| < 1e18 |
| currency | string | no | |
| period | string | no | |
| statement_period | string | no | |
| statement_period_end | string | no | date-like when present |
| period_type | string | no | one of: `quarterly`, `half_yearly`, `annual`, `point_in_time`, `other`, `unknown` |
| period_scope | string | no | one of: `flow`, `stock`, `unknown` |
| period_length_months | int | no | `0/3/6/12` typically |
| period_inference_source | string | no | inference provenance |
| reporting_cadence | string | no | one of: `quarterly`, `half_yearly`, `annual`, `other`, `unknown` |
| reporting_period_months | int | no | `0/3/6/12` typically |
| reporting_cadence_inference_source | string | no | inference provenance |
| balance_position | string | no | |
| balance_date | string | no | |
| integrity_score | int | no | 0..integrity_score_max |
| integrity_checks_evaluated | int | no | ≥ 0 |
| integrity_checks_passed | int | no | ≥ 0 |
| integrity_score_max | int | no | typically 4 |
| confidence | float | no | [0.0, 1.0] |
| canonical_confidence_score | int | no | 0..4 (or max defined in code) |
| canonical_tier | string | no | `strict` or `table_promoted` |
| canonical_promotion_reason | string | no | original context reason for promoted rows |
| promoted_to_canonical_tier | bool/int | no | set on context source rows when promoted |
| statement_scope | string | no | |
| statement_title | string | no | |
| statement_family | string | no | |
| block_id | string | no | |
| table_id | string | no | |
| table_page | int | no | ≥ 0 |
| page_number | int | no | ≥ 0 |
| source_mode | string | no | e.g. table_bbox, parse_error, ocr |

## Rules

1. **Type checks:** `value_type` in `{"amount", "percent", "text"}`. For `amount`/`percent`, `value` must be numeric (int/float).
2. **Numeric sanity:** For `value_type == "amount"` or `"percent"`, `value` must be finite; recommend |value| < 1e18.
3. **Required:** `file`, `metric`, `value_type` non-empty for canonical rows.
4. **Confidence:** `confidence` in [0, 1]; `canonical_confidence_score` within defined range.
5. **Canonical provenance:** if `canonical_tier == "table_promoted"`, `canonical_promotion_reason` should be non-empty.
6. **Period semantics:** use `period_scope=stock` for point-in-time balance metrics; use `period_scope=flow` + cadence fields for income/cash-flow comparability checks.

## Implementation

- Add `validate_canonical_row(row) -> list[str]` in `scripts/extract_financial_metrics.py` returning error messages.
- Call before writing (e.g. filter or log invalid rows) or in a separate script that reads JSON/CSV and reports errors.
