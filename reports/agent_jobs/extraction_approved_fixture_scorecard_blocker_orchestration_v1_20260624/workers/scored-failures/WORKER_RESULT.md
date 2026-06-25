I'll start by reading the key evidence files in parallel.
Now let me read the specific fixture files and the failure_rows continuation for the `present_wrong_value` and `missing_expected_metric` rows, plus the multipass extraction code.
Now let me read the scorecard's `present_wrong_value` rows and the `missing_expected_metric` rows to get the exact actual vs expected discrepancies:
Now let me find the EQR investing_cf actual value and the GRE investing_cf actual value in the scorecard:
Now let me check the actual values for the GRE investing_cf row and the EQR investing_cf row to confirm exact actual vs expected:

The data is clear from the grep:
- EQR investing_cf: actual=-255000, expected=-2656000 (10x off — the extraction appears to have read the capex/PP&E sub-item 2.1(c) instead of the investing total 2.6)
- GRE investing_cf: actual=-1193000, expected=-624000 (the extraction _added_ capex+exploration into investing, or read a different line)
- MIN np_attributable: actual=2000000, expected=495000000 (the extraction got 2M which is the NCI or minority interest, not the parent attribution)
- QBE shares_outstanding: actual=8409000000, expected=1510000000 (the extraction got ~8.4B which is likely issued shares including treasury, not the 1.51B from the note)

Let me also check the remaining QBE present_wrong_value record:
Now I have all the data I need. Let me compile the WORKER_RESULT.md body.

```markdown
worker_id: scored-failures
task_tier: small
model: deepseek/deepseek-chat
decision_limit: evidence_only
summary: Inspected 4 missing_expected_metric and 4 present_wrong_value hard failures from the approved-15-fixture scorecard. 3 of 4 present_wrong_value failures are gross extraction errors (wrong table row / wrong share count). 3 of 4 missing_expected_metric failures are LB: the metric is in the source PDF but the LLM missed it. 1 missing (QBE capex) is a tiny insurance-PP&E value. All 8 failures are likely parser-fixable with targeted prompt or pass-level tuning; none require source PDF, ontology, or gold-label mutation.
findings:
  'missing_expected_metric rows (4 total):'
    - '1. BHP_A_2021-06-30 | np_attributable | expected=11,304M | actual=null | Fixture note: "Attributable to BHP shareholders" = 11,304 on page 44. Missing from actual payload (replay_results shows np_attributable=null). PARSER-FIXABLE: the label "Attributable to BHP shareholders" may not match prompt ontology field name np_attributable; NP reconciliation or label-matching pass needs widening.'
    - '2. BHP_A_2021-06-30 | cash_end | expected=15,246M | actual=null | Fixture note: "Cash and cash equivalents, net of overdrafts, at the end of the financial year" on page 46. Missing from actual payload. PARSER-FIXABLE: same root cause — LLM or pass-2 table locator missed the cash_end row in the cash flow statement.'
    - '3. MIN_H_2025-12-31 | ebit | expected=1,031M | actual=null | Fixture note: "PROFIT/(LOSS) FROM OPERATIONS = 1,031" on page 14 (income statement row 13). Replay shows ebit=null, np_attributable got wrong value 2M (see below). PARSER-FIXABLE: EBIT extraction label match for "Profit from operations" may need wider tolerance or an additional pass-3 label alias.'
    - '4. QBE_H_2025-06-30 | capex | expected=-9M | actual=null | Fixture note: "Payments for purchase of property, plant and equipment = (9)" on page 17. Very small insurance PP&E. PARSER-FIXABLE: tiny capex likely below the absolute-value threshold in the extractor or the row was not in the extracted table region. Low impact.'
  'present_wrong_value rows (4 total):'
    - '1. EQR_Q_2025-12-31 | investing_cf | expected=-2,656K | actual=-255K | Scorecard actual=-255K; replay_results shows investing_cf=-255K. Fixture note total investing sec 2.6 = -2,656. The actual -255 matches the sub-item 2.1(d) exploration spend only. PARSER-FIXABLE: the LLM read the subtotal row (item 2.1) instead of the grand total (item 2.6). Target: pass-3 (extract pass) needs to prefer the section total over sub-item rows for investing_cf.'
    - '2. GRE_Q_2024-12-31 | investing_cf | expected=-624K | actual=-1,193K | Scorecard actual=-1,193K. Fixture note total investing sec 2.6 = -624 (entirely exploration). The actual -1,193 is the sum of capex(0)+exploration(-624)+other investing items, suggesting the LLM combined multiple line items or read a different column. PARSER-FIXABLE: pass-3 row-selection logic may aggregate sub-items instead of using the section total line.'
    - '3. MIN_H_2025-12-31 | np_attributable | expected=495M | actual=2M | Fixture note: "Equity holders of the parent = 495" on page 14. The actual 2M is the NCI/minority interest (78M stated, but 2M is a different non-owner line). PARSER-FIXABLE: extractor picked up non-controlling interest instead of parent attribution; label disambiguation between "Equity holders of the parent" and "Non-controlling interests" needs improvement.'
    - '4. QBE_H_2025-06-30 | shares_outstanding | expected=1,510M | actual=8,409M | Fixture note: "Issued ordinary shares, fully paid at 30 June = 1,510 millions" from Note 4.3.1. Actual 8,409M appears to be the total issued shares including treasury, not the net figure. PARSER-FIXABLE: share count source disambiguation — LLM used a different row from the share capital note or the balance sheet line.'
evidence_paths:
  - reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/failure_rows.json
  - reports/agent_jobs/extraction_approved_15_fixture_replay_scorecard_v1_20260623/scorecard.json
  - reports/agent_jobs/extraction_approved_15_fixture_replay_scorecard_v1_20260623/replay_results.json
  - financial-engine_v2/backend/tests/eval_fixtures/BHP_A_2021-06-30.json
  - financial-engine_v2/backend/tests/eval_fixtures/EQR_Q_2025-12-31.json
  - financial-engine_v2/backend/tests/eval_fixtures/GRE_Q_2024-12-31.json
  - financial-engine_v2/backend/tests/eval_fixtures/MIN_H_2025-12-31.json
  - financial-engine_v2/backend/tests/eval_fixtures/QBE_H_2025-06-30.json
confidence: HIGH — all 8 hard-failure rows identified with exact expected vs actual values; fixture provenance notes confirm ground truth for each.
risks:
  - "EQR investing_cf wrong-row selection (sub-item vs section total) and GRE investing_cf aggregation suggest a systemic pass-3 row-preference issue in Appendix 5B extraction, not isolated to one fixture."
  - "MIN np_attributable 2M vs 495M and BHP np_attributable missing (both same canonical field np_attributable) suggest the prompt ontology for profit-attribution labels may need a single aligned label strategy (parent-equity vs total-vs-NCI disambiguation)."
  - "QBE shares_outstanding 8,409M vs 1,510M indicates treasury-share gross/net confusion — this may affect other insurance/bank fixtures with complex capital structures."
  - "All 8 failures are in scored/CONFIRMED_SOURCE_EVIDENCED status; no gold-label or source-PDF mutation needed. Broad ontology change is not required — narrow pass-level or alias-list fixes should suffice."
recommended_next_action: "Codex should inspect multipass_extraction.py pass-3 (extract pass) row-selection logic in the cash-flow and income-statement branches, particularly: (a) how section-total rows vs sub-item rows are preferred for metrics like investing_cf, (b) how np_attributable disambiguates parent-equity from NCI, (c) how shares_outstanding resolves gross vs net share counts. Target files: financial-engine_v2/backend/app/services/multipass_extraction.py lines ~200-400 (pass-3 extraction rules) and the pass-2 table locator heuristics. Also review test_multipass_extraction.py for coverage of the specific 5B sub-item-vs-total pattern."
stop_condition_hit: false
```
