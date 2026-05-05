# Risks And Blockers

- Live cleanup remains blocked until all approval gates pass.
- Current schema has `active` and `expired`, but no `quarantined`; quarantine candidates cannot execute without a schema/store migration and retrieval filter review.
- Expiry is not perfectly reversible by itself because it mutates status/timestamps; rollback requires a DB backup and change-log/audit manifest.
- Source titles and evidence spans are incomplete for many rows, especially newspaper4k rows.
- Raw dict-like rows may contain useful facts and must not be auto-expired solely because of formatting.
- Alias canonicalization is high risk and remains blocked until authoritative identity evidence exists.
- Market/macro rehome is blocked until destination semantics and audit trail are approved.
- Direct live `mode=ro` SQLite inspection failed in this shell, so future work should copy DBs before analysis.
- The secondary `.cursor/rules/*.md` architecture files referenced by the architecture-check skill were DATA_MISSING in this repo checkout; SYSTEM_CONTRACT.md remained the controlling contract evidence.
