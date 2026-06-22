# Worker C: WHC Scale-Unknown Proof Packet

## Result

Implementation-ready only for the existing WHC FY22 opt-in/openability path.
No broad WHC scale repair was integrated.

## Evidence

- Exact source PDF: `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/WHC/financial_performance/2022-09-21_2022-annual-report_9640d9f1-a45b-492d-8df5-9bad0f46431c.pdf`.
- Existing source smoke artifacts show rows on pages 57, 58, and 60, with scale evidence on pages 57, 58, and 61.
- Existing post-fix exact replay artifacts show `ok`, `period_end=2022-06-30`, `scale=thousands`, and metric source scales from table evidence for eight canonical metrics.

## Decision

Do not use WHC FY22 as broad scale repair proof.
Keep WHC as an opt-in/openability-selected-table guard path with explicit pages `[57, 58, 60, 61]`.
Fail closed outside explicit period, scale, and row-candidate provenance.
