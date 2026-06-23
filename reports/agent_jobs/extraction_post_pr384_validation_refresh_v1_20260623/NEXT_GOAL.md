# Next Goal

Create a clean source-row proof lane from current
`origin/migration/clean-runtime-baseline-reconstruct-v1` for the remaining row
issues:

1. DXC `f8a24788-dbe0-48f7-ad41-654f2c8a3845`: capture exact rows around
   `net operating income`, including document/page/table, period, unit, value,
   surrounding labels, and whether the source proves a canonical EBIT mapping.
2. WHC `9640d9f1-a45b-492d-8df5-9bad0f46431c`: capture exact rows/table
   headers for scale metadata and per-metric row references, checking PR #340
   as related evidence but not treating it as merged truth.
3. End with one of `FIX_PROVEN`, `NO_FIX_PROVEN`, or `DATA_MISSING`.

Do not implement a product change unless the source rows explicitly prove a
narrow mapping or scale binding. Green replay status alone is not enough.
