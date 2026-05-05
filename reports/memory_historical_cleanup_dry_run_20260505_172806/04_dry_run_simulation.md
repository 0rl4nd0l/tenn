# Dry Run Simulation

## Action Simulated

Only `status_expire_candidate` was simulated. Alias merge, market/macro rehome, quarantine, manual-review mutation, blocked/uncertain mutation, preserve mutation, retrieval tuning, and production code changes were not simulated.

## Copied-DB Mutation

For each validated row id, the script updated only `memory_entries.status` from `active` to `expired` in the copied DB and inserted one copied-DB `change_log` row with `event_type='dry_run_expire'`. It did not rewrite statement text, source fields, provenance fields, `first_seen_at`, `last_seen_at`, `closed_at`, or metadata.

## Results

- Rows that would expire: 1212
- Rows skipped: 0
- Before status counts: {'active': 1997, 'expired': 1}
- After status counts: {'active': 785, 'expired': 1213}
- Row total before/after: 1,998 / 1,998
- Change-log rows after dry run: 3683

No candidate required DELETE, alias canonicalization, market/macro rehome, or production code changes.
