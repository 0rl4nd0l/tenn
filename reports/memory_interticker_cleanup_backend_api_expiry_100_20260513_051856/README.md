# Memory Interticker Backend API Expiry Pilot 100

Lane: Memory
Branch: preserve/dirty-work-20260430T065748Z
Worktree: /mnt/hdd-data/home/l4nd0/tenn
Execution mode: SAFE EXTENSION MODE
Contested surfaces touched: none
Collision risk: HIGH for live DB mutation
Decision: proceed after explicit user approval for 100-row pilot

## Contract Position

Target layer: Storage and Retrieval-adjacent Memory.
Relevant rules: SYSTEM_CONTRACT.md sections 1.1, 1.2, 1.3, 2.1, 2.2, and data/source integrity rules in 3-4.
Must not change: canonical financial truth, market/user/session memory boundaries, Qdrant, retrieval ranking, answer synthesis, source labels, or production routing.
Why safe: this cleanup used the backend-owned manual expiry endpoint for exactly 100 approved candidate rows, preserved a pre-mutation backup, and wrote row-level audit artifacts.
GPU process check required: no; this task did not spawn, restart, or depend on llama-server.

## Approval

- User approval: `proceed` after confirming the first batch should start with `100` rows.
- Approval id: `approved_by_user_20260513_backend_api_pilot_100_20260513_051856`
- Source manifest: `reports/memory_interticker_contamination_manifest_20260513_043646/csv/approval_required_status_expire_candidates.csv`
- Max rows: `100`

## Execution Note

An initial direct status-only SQLite transaction attempt was blocked before mutation because the live company-memory DB is root-owned and this shell cannot acquire a write transaction. Non-interactive sudo is unavailable. The pilot therefore used the official backend expiry endpoint: `POST /api/context/memory/company/expire`.

That endpoint sets `status = expired` and also updates `closed_at` / `last_seen_at` according to the existing backend API semantics.

## Backup

- Backup DB: `/mnt/hdd-data/home/l4nd0/tenn_runtime_backups/memory_interticker_cleanup_backend_api_expiry_100_20260513_051856/company_memory.sqlite.pre_backend_api_expiry_100`
- Backup method: `raw_file_copy`
- Backup SHA256: `72a33bb11ee537ddbd6e7ed3c03d279c57f8fe2dba61f677e574972e150d6e1b`

## Result

| item | before | after |
|---|---:|---:|
| active rows | 2083 | 1983 |
| expired rows | 250 | 350 |
| active duplicate clusters | 94 | 94 |
| active duplicate rows | 1615 | 1515 |

## Verification

- Rows requested: `100`
- Rows expired: `100`
- Target rows still active: `0`
- Non-target memory-entry core diffs: `0`
- Rows skipped before selection because the backend API cannot accept their stored company id: `32`

## Files

- `csv/approved_backend_api_pilot_candidates.csv` - exact 100 manifest rows selected for this API pilot.
- `csv/backend_api_expiry_results.csv` - HTTP result for every expiry call.
- `csv/live_rows_expired.csv` - rows verified expired in live storage.
- `csv/skipped_before_selection.csv` - approved manifest rows skipped before selection, mostly non-API-compatible company ids.
- `live_cleanup_metadata.json` - machine-readable cleanup metadata and counts.
- `sql_templates/DO_NOT_RUN_rollback_backend_api_expiry_100.sql` - row-id rollback template; backup restore remains preferred for full rollback.
