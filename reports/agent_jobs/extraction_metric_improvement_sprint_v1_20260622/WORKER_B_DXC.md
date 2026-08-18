# Worker B: DXC Metric-Label Mismatch Proof

## Result

`NO_FIX_PROVEN`.

## Evidence

Read-only worker classification found the current DXC gate is valid for canonical `ebit`.

- Source: `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/DXC/financial_performance/2025-08-11_fy25-results-presentation_f8a24788-dbe0-48f7-ad41-654f2c8a3845.pdf`.
- Page 26 / slide 25: `Consolidated profit & loss statement`, `$'000`.
- Rows include `Total revenue 46,547`, `Finance costs (11,412)`, `Total expenses (16,985)`, `Net operating income 29,562`, `Net profit/(loss) after tax 39,374`.
- No explicit `EBIT` row was found.

## Decision

Do not relax `_EBIT_LABEL_BLOCKERS`.
Do not map `net_operating_income` to canonical `ebit`.
Keep the focused regression expecting `validation_gate:metric_label_mismatch:ebit:net_operating_income`.
