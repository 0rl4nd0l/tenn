# Rollback

## Primary Rollback

Preferred rollback is restoring the raw pre-mutation backup preserved outside git:

`/mnt/sdb2/home/l4nd0/tenn_runtime_backups/memory_cleanup_20260505_174752/live_expiry_backup/company_memory.sqlite.pre_live_expiry_20260505_174752`

Backup checksum:

`aa25e14894be56d601ce4ec9b4fd48e67eaf94b6cf60db13eae52c00c90ba5b1`

This matches the live company memory DB checksum captured before the approved live expiry batch.

The original in-report backup artifact was removed from git tracking during backup artifact remediation. Do not commit raw SQLite rollback copies.

## Row-Id Rollback

The report also includes:

- `sql_templates/DO_NOT_RUN_rollback_live_expire_first_batch.sql`

That template restores the 249 approved `entry_id`s from `expired` to `active`, inserts `rollback_expire` audit rows, and refreshes summary counts. Prefer the full backup restore if any unexpected DB activity occurred after this cleanup.

## Non-Rollback Scope

No rollback is needed for market memory, thesis memory, session state, Qdrant, ingestion, retrieval/ranking, source labels, or financial truth because this cleanup did not touch those surfaces.
