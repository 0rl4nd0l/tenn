# Dry Run Design

Dry run should use copied DBs only and should never attach to live DBs.

Suggested copied-DB validation:

1. Verify `csv_checksums.sha256`.
2. Load `csv/memory_rows_expire_candidates.csv`.
3. Confirm each candidate row id exists in copied `memory_entries` and is still `active`.
4. Confirm source_id, company_id, statement, and duplicate_cluster_id match the report.
5. Simulate `UPDATE memory_entries SET status='expired'` on copied DB only, inside a transaction that is rolled back or discarded.
6. Insert simulated change_log rows in the copy only if the dry-run wants to validate change-log counts.
7. Report active-row deltas by company_id and cluster.

## Read-Only Validation

Commands run:

```bash
python3 - <<'PY'
import pathlib
root = pathlib.Path("reports")
print("reports exists", root.exists())
PY

git diff --check
```

Also run against copied DBs only:

```bash
sqlite3 /tmp/tenn_memory_cleanup_plan_20260505_LIUc2l/company_memory.sqlite '.schema'
sqlite3 /tmp/tenn_memory_cleanup_plan_20260505_LIUc2l/market_memory.sqlite '.schema'
sha256sum /tmp/tenn_memory_cleanup_plan_20260505_LIUc2l/company_memory.sqlite /tmp/tenn_memory_cleanup_plan_20260505_LIUc2l/market_memory.sqlite /tmp/tenn_memory_cleanup_plan_20260505_LIUc2l/source_registry.jsonl /tmp/tenn_memory_cleanup_plan_20260505_LIUc2l/commentary_memos.jsonl /tmp/tenn_memory_cleanup_plan_20260505_LIUc2l/news_memos.jsonl
```

Live DB note: direct `sqlite3 file:...company_memory.sqlite?mode=ro` against the root-owned live data path returned `attempt to write a readonly database`, so row analysis was performed only after copying DB files to `/tmp/tenn_memory_cleanup_plan_20260505_LIUc2l/`.

Validation results from this audit:

```text
reports exists True
row_level_total 1998
git diff --check passed
```
