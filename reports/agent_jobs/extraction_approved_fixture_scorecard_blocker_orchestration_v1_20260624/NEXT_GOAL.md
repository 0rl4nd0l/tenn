# Next Goal

Implement the board-approved deterministic extractor fixes:

1. Formal income-statement recovery for source-proven EBIT and attributable
   NPAT rows.
2. Appendix 5B current-quarter section-total recovery for operating,
   investing, and financing cash-flow totals.
3. Exact cash-end recovery for `cash and cash equivalents, net of overdrafts`
   year-end rows.
4. Tiny PP&E capex recovery when scale is millions and the row label is strong.
5. Share-count column recovery that prefers `NUMBER OF SHARES` columns over
   adjacent currency amount columns.

Then run focused tests, full `test_multipass_extraction.py`, approved
15-fixture no-write replay, and #97 scorecard. Do not mutate gold labels,
canonical truth, prompts, schema, DB, source PDFs, or count-24/count-32.
