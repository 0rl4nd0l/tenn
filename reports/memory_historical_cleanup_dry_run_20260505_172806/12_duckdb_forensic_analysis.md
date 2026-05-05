# DuckDB Forensic Analysis

DuckDB status: UNTESTED. The DuckDB CLI was not found and Python `duckdb` import raised `ModuleNotFoundError`; no dependency was installed.

Equivalent checks were completed with Python, CSV, and SQLite:

1. Expiry candidates do not overlap preserve/manual/blocked cohorts: passed (0/0/0).
2. Candidate row total reconciles to 1,998 company-memory rows: passed.
3. Expiry candidates ranked by fanout cluster confidence: represented by `csv/operator_first_batch_candidates.csv` and cluster counts in `03_candidate_validation.md`.
4. Ticker scopes with largest active-row reduction: `csv/post_dry_run_counts_by_entity.csv` and `05_before_after_counts.md`.
5. Nearly emptied scopes: none under strict floor 3.
6. Strong-provenance candidates needing manual review: none found among the 1,212 first-action candidates; all had stable source/source_id and no preserve/manual/blocked overlap.
7. Recommended first batch of obvious duplicate fanout rows: 249 rows in `csv/operator_first_batch_candidates.csv`.
