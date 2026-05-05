# Rollback Readiness

## Reversibility

- Can the copied-DB status change be reversed by row_id? yes. `dry_run_rows_expired.csv` preserves every affected `entry_id` and original status.
- Does the status-only approach preserve original row content? yes for statement, type, source, source_id, confidence, materiality, persistence, first_seen_at, last_seen_at, closed_at, and metadata.
- Are timestamps/provenance preserved in this dry run? yes for `memory_entries`; only `status` changed and copied-DB `change_log` rows were appended.
- Would future live cleanup need a backup snapshot? yes.
- Would future live cleanup need audit entries? yes. The copied DB has `change_log`, and the live template should insert one audit row per expired `entry_id`.

## Caveat

The current `CompanyMemoryStore.expire_entry()` API updates `closed_at` and `last_seen_at`. If the operator requires timestamp preservation exactly as proven here, the future live cleanup should use an explicitly approved status-only maintenance transaction plus audit rows, not the manual expire API loop.
