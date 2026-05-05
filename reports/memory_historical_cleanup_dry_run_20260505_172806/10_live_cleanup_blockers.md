# Live Cleanup Blockers

Live cleanup is still blocked unless a separate live cleanup prompt grants explicit operator approval.

Remaining blockers and gates:

- No live DB mutation is authorized in this lane.
- A backup snapshot is required before live status expiry.
- A writer-free maintenance window or equivalent lock discipline is required.
- The current schema has no `quarantined` status, so quarantine remains blocked.
- Alias merge/rewrite remains blocked pending identity audit and source-preserving alias map.
- Market/macro rehome remains blocked pending destination semantics and audit plan.
- Existing API expiry mutates `last_seen_at`/`closed_at`; timestamp-preserving status-only SQL needs explicit approval if used live.
- Rows excluded from the first batch remain candidates for later batches or manual review, not automatic mutation.
