# Summary

## Final Verdict

Did any live DB change? no. The live company memory DB checksum after the dry run was still `aa25e14894be56d601ce4ec9b4fd48e67eaf94b6cf60db13eae52c00c90ba5b1`, matching the pre-copy checksum recorded in this run.

Did the copied-DB dry run complete? yes. The copied DB checksum changed from `aa25e14894be56d601ce4ec9b4fd48e67eaf94b6cf60db13eae52c00c90ba5b1` to `1358344ca9001ea6ac03d708a2298b5939b6052d8d59bc5075e785eeffd96d2a` after status-only expiry simulation and copied-DB `change_log` inserts.

Candidate rows found: 1212.
Rows expired in copied DB: 1212.
Rows skipped: 0.
Preserve/manual/blocked overlap with expiry candidates: 0/0/0.

## Counts

- Company-memory row total: 1998; copied DB row total: 1,998.
- Active rows: 1997 before, 785 after.
- Expired rows: 1 before, 1213 after.
- Change-log rows: 2,471 before, 3683 after; the added copied-DB events use `dry_run_expire`.
- Recommended first live batch: 249 rows.
- Excluded from first live batch: 963 rows, deferred for later batches or separate review.

## Go/No-Go

GO: request a future live cleanup lane for the 249-row first batch only, with explicit operator approval, backup snapshot, maintenance window, and row-id manifest.

NO-GO: do not execute live cleanup automatically from this audit. Quarantine, alias merge/rewrite, and market/macro rehome remain blocked.
