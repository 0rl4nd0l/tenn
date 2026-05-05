# Backup And Rollback Plan

Minimum future cleanup backup procedure:

1. Stop any memory-writing job or obtain operator confirmation that no ingestion/commentary memo dispatch is running.
2. Record live DB paths for `company_memory.sqlite`, `market_memory.sqlite`, and any `-wal`/`-shm` files present.
3. Copy DB plus WAL/SHM files to `backups/memory_cleanup_<timestamp>/` or another operator-approved path.
4. Run `sha256sum` for copied DBs and candidate CSVs.
5. Record pre-cleanup row counts: total rows, active rows, expired rows, rows by company_id, and change_log count.
6. Execute status-only mutations inside one SQLite transaction with an expected affected-row count.
7. Roll back immediately if any row id is missing, status is not `active`, affected count differs, or SQLite returns busy/locked beyond the approved retry policy.
8. Post-cleanup, record total row count, active/expired diff, change_log diff, and sample verification for every target cohort.
9. Restore procedure: stop writers, replace live DB/WAL/SHM from approved backup, verify checksum, restart only after row counts match backup manifest.

Operator checkpoints: backup path, backup checksum, candidate CSV checksum, allowed action type, maximum rows to mutate, sample rows approved, and post-cleanup sampling accepted.
