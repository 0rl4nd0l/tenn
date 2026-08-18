
# DXC Source-Row Proof

Classification: `NO_FIX_PROVEN`

Target failure: `metric_label_mismatch:ebit:net_operating_income`

Source PDF: `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/DXC/financial_performance/2025-08-11_fy25-results-presentation_f8a24788-dbe0-48f7-ad41-654f2c8a3845.pdf`

Evidence: page 26 / slide 25, `Consolidated profit & loss statement`, `$'000`, FY25.

Rows:
- `Total revenue`: 46,547
- `Finance costs`: (11,412)
- `Total expenses`: (16,985)
- `Net operating income`: 29,562
- `Net profit/(loss) after tax`: 39,374

Decision: no EBIT row is present. Because finance costs are explicit in the same table, `net operating income` is not safe global evidence for EBIT. No code fix implemented for DXC.
