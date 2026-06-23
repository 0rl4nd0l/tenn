
# WHC Source-Row Proof

Classification: `FIX_PROVEN`

Target failure: annual report publication/title date used as `period_end`.

Source PDF: `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/WHC/financial_performance/2022-09-21_2022-annual-report_9640d9f1-a45b-492d-8df5-9bad0f46431c.pdf`

Pre-fix failure: `validation_gate:period_end_source_mismatch:payload=2022-09-21:source=2022-06-30:year_ended_explicit_date`.

Source proof:
- Period evidence: `For the year ended 30 June 2022`; period type `A`; source period end `2022-06-30`.
- Unit evidence: table-derived `thousands`; currency `AUD`.
- Page 57 income statement rows include `Revenue 21 4,920,102 1,556,976`, `Profit/(loss) before net financial expense 2,821,254 (706,181)`, and `Net profit/(loss) for the year 1,951,965 (543,914)`.
- Page 60 cash-flow rows include `Net cash from operating activities 3.4 2,529,823 138,765`, `Purchase of property, plant and equipment (124,210) (68,693)`, and `Cash and cash equivalents at end of year 1,215,460 95,202`.

Note: the source PDF is copy-restricted, so normal `pdftotext` did not expose row text. This proof uses the current no-write replay structured/openability evidence and row refs.

Post-fix replay: `ok`, period end `2022-06-30`, validation failures `0`.
