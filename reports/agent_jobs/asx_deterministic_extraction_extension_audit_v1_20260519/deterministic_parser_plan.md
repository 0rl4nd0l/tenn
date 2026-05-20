# Deterministic Parser Plan

Job: `asx_deterministic_extraction_extension_audit_v1_20260519`

This plan is design-only. It does not authorize parser routing, source-code changes, extraction jobs, canonical writes, gold-label edits, runtime changes, DB writes, Qdrant writes, memory writes, or production extraction claims.

## Appendix 5B Line-Item Parser

Source anchors:
- `Appendix 5B` title or equivalent mining/oil and gas exploration quarterly cash-flow report language.
- Line-numbered sections 1 through 8.
- Line `1.9 Net cash from / (used in) operating activities`.
- Column labels such as `Current quarter $A'000` and `Year to date $A'000`.
- Period header such as quarter ended date.

Metric candidates:
- `operating_cash_flow`: line 1.9 current-quarter value.
- `investing_cf`: investing section net cash line when explicitly labelled.
- `financing_cf`: financing section net cash line when explicitly labelled.
- `capex`: only explicit allowed sub-item sums under the current system contract.
- `cash_end`: cash and cash equivalents at end of period when line-labelled.

Evidence binding:
- `document_id`, source PDF path/checksum, page number, Appendix page number if present, table id, row number, line number, row label, column label, raw value, normalized value, currency, scale, and parser warnings.

Trust and abstain rules:
- Abstain if current-quarter and YTD columns collapse.
- Abstain if only narrative text is available.
- Abstain if line number and label disagree.
- Abstain for revenue/EBIT/NPAT/net debt/shares unless those metrics are separately explicit outside the 5B cash-flow form.
- Do not map customer receipts to accrual revenue.

Output artifact shape:
- One JSON object per document with `document_type`, `period`, `period_end`, `currency`, `scale`, `tables`, `line_items`, `metric_candidates`, `arithmetic_checks`, `abstain_reasons`, and `canonical_write=false`.

Tests needed:
- Current-quarter vs YTD disambiguation.
- Parentheses/sign normalization.
- Page-spanning table continuation.
- Missing line abstain.
- Capex explicit-subitem sum only.
- Expected-null income-statement metrics for Appendix 5B fixtures.

## Appendix 4C Parser

Source anchors:
- `Appendix 4C`.
- `Quarterly cash flow report`.
- Listing Rule 4.7B language.
- Cash-flow section rows and current-quarter/YTD columns.

Metric candidates:
- Operating, investing, financing cash flow.
- Capex only when property/plant/equipment or equivalent explicit cash outflow row is present.
- Cash end when explicitly row-labelled.

Evidence binding:
- Same as Appendix 5B, with `asx_form=appendix_4c`.

Trust and abstain rules:
- Cashflow-only by default.
- Revenue, EBIT, NPAT, net debt, and shares remain absent unless separately explicit in a formal statement.
- Abstain on 4C/5B ambiguity or missing current-quarter column.

Output artifact shape:
- Same normalized line-item candidate schema as Appendix 5B, with form-specific line mappings.

Tests needed:
- 4C vs 5B classifier separation.
- Expected-null tests for income-statement metrics.
- Current-quarter/YTD column preservation.

## Appendix 4D / 4E Summary Table Parsers

Source anchors:
- `Appendix 4D` or `Appendix 4E`.
- `Results for announcement to the market`.
- Rows such as revenue from ordinary activities, profit/loss from ordinary activities, net profit/loss attributable, dividends, NTA, EPS.
- Formal statement table titles when present.

Metric candidates:
- `revenue` from explicit revenue ordinary activities rows or statement revenue rows.
- `np_attributable` from explicit profit attributable rows.
- `ebit` only when explicitly labelled or unambiguously statement-derived under an approved future contract.
- Cash-flow metrics from formal cash-flow statement tables, not from movement percentages.
- EPS, NTA, EBITDA, dividends, and total debt remain unsupported/review-only unless schema support is added in a separate task.

Evidence binding:
- `summary_table` and `statement_table` candidates are separate.
- Each metric candidate records whether it came from Appendix summary, statement table, note, or reconciliation.

Trust and abstain rules:
- Prefer formal statement table evidence when Appendix summary and statement disagree.
- Abstain on percentage-only movement rows.
- Abstain on unsupported metric rows.
- Abstain on derived net debt unless the source explicitly states net debt as a row/value.

Output artifact shape:
- `appendix_summary_candidates`, `statement_candidates`, `unsupported_metric_candidates`, `conflicts`, `abstain_reasons`, and `canonical_write=false`.

Tests needed:
- Appendix 4D half-year unit row detection.
- Appendix 4E annual unit row detection.
- Current vs prior-period column selection.
- Summary-table conflict handling.
- Unsupported EPS/NTA/EBITDA stays review-only.

## Annual / Half-Year Statement Table Selector

Source anchors:
- Consolidated statement of profit or loss / comprehensive income.
- Consolidated statement of cash flows.
- Statement of financial position.
- Statement of changes in equity or share capital note.
- Net debt note only when explicit point-in-time row evidence exists.

Metric candidates:
- Existing schema-supported metrics only unless a separate schema task expands support.

Evidence binding:
- Table title/caption, page, headers, current-period column, row label, raw value, normalized value, currency, scale, and statement type.

Trust and abstain rules:
- Reject segment tables, glossary tables, management discussion snippets, and generic note tables unless explicitly selected for the metric.
- Abstain when current-period column cannot be selected deterministically.
- Do not infer net debt from components for canonical truth without explicit source row and approved gate.

Output artifact shape:
- `statement_table_rankings`, `selected_statement_tables`, `metric_candidates`, `rejected_tables`, `abstain_reasons`, and `canonical_write=false`.

Tests needed:
- Table ranking stability.
- Segment/reconciliation table rejection.
- Share count row selection.
- Net-debt note explicit-row selection.
- Non-AUD downgrade/abstain behavior preserved.

## Smallest Safe Sequence

1. Add fixture/schema-only ASX document-type contract artifacts. Allowed files should be task card, fixture JSON files, and report artifacts only.
2. Add pure classifier unit tests and a pure classifier module that is not imported by production routing.
3. Add read-only comparator artifact schema and writer over pre-existing structured documents or static fixtures.
4. Add Appendix 5B/4C/4D/4E parser prototypes that emit sidecar artifacts only.
5. Run canonical_core, expanded_required, and confirmed_metric_coverage measurement gates before any routing discussion.
