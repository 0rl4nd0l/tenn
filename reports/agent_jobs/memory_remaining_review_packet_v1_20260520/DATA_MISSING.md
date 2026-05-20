# DATA_MISSING

This packet did not reopen production SQLite and did not call live routes.
Missing evidence is represented explicitly rather than filled from live stores.

## Missing Row / Source Detail

- Full row text beyond the capped statement previews in prior artifacts.
- Full source article/transcript content and source spans for every row.
- Statement preview for `entry_id=717`; the live inventory artifact included the row ID and company/source context but capped the preview list before this row.
- Per-row writer job ID, writer batch ID, source memo row ID, and explicit ticker-attribution reason; prior audits noted these are not durable fields in the company-memory schema.

## Missing Current DB Fields

- Current row metadata beyond fields already present in `known_historical_source_checks.json`, `active_source_fanout_clusters.csv`, and `candidate_entry_id_status_check.json`.
- Any changes after the 2026-05-19 live read-only inventory artifact.

## Missing Live Surfacing Proof

- No live chat, `/api/context/company_dump`, Cockpit Memory Workbench, or source drawer calls were made because those paths may write session/read/event artifacts.

## Boundary

Production DB reads, source-content review, backup/checksum, and any expiry require a separate explicitly approved task.
