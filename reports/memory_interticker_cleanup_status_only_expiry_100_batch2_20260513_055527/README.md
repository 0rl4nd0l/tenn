# Memory Interticker Status-Only Expiry Batch 2 - 100 Rows

Lane: Memory
Branch: preserve/dirty-work-20260430T065748Z
Worktree: /mnt/hdd-data/home/l4nd0/tenn
Execution mode: SAFE EXTENSION MODE
Contested surfaces touched: none
Collision risk: HIGH for live DB mutation
Decision: proceed after explicit user approval for another 100-row batch

## Contract Position

Target layer: Storage and Retrieval-adjacent Memory.
Relevant rules: SYSTEM_CONTRACT.md sections 1.1, 1.2, 1.3, 2.1, 2.2, and data/source integrity rules in 3-4.
Must not change: canonical financial truth, market/user/session memory boundaries, Qdrant, retrieval ranking, answer synthesis, source labels, or production routing.
Why safe: this cleanup expired exactly 100 active approved candidate rows by status only, preserved a pre-mutation backup, wrote change-log entries, and recomputed company active counts.
GPU process check required: no; this task did not spawn, restart, or depend on llama-server.

## Approval

- User approval: `proceed` after the first 100-row pilot completed.
- Approval id: `approved_by_user_20260513_status_only_batch2_100_20260513_055527`
- Source manifest: `reports/memory_interticker_contamination_manifest_20260513_043646/csv/approval_required_status_expire_candidates.csv`
- Max rows: `100`

## Execution Note

The backend API became unavailable before this batch: `fe_backend` exited and restart failed during Qdrant startup validation because Ollama embedding probe returned HTTP 500. This batch therefore used a root-owned backend worker container transaction against `/data/reports/research_memory/company_memory.sqlite`.

Mutation semantics for this batch are status-only: `status = expired`, change-log rows inserted, `company_memory.active_entry_count` recomputed. `last_seen_at` and `closed_at` were preserved for target rows.

## Backup

- Backup DB: `/mnt/hdd-data/home/l4nd0/tenn_runtime_backups/memory_interticker_cleanup_status_only_expiry_100_batch2_20260513_055527/company_memory.sqlite.pre_status_only_expiry_100_batch2`
- Backup method: `raw_file_copy_with_sidecars_if_present`
- Backup SHA256: `a851967d440d66a6370a4ec1144bd088740c63674633c3e7faf67217a20543b2`

## Result

| item | before | after |
|---|---:|---:|
| active rows | 1983 | 1883 |
| expired rows | 350 | 450 |
| active duplicate clusters | 94 | 94 |
| active duplicate rows | 1515 | 1415 |

## Verification

- Rows requested: `100`
- Rows expired: `100`
- Target rows still active: `0`
- Target expire change-log rows: `100`
- Non-target memory-entry core diffs: `0`

## Files

- `csv/approved_status_only_batch2_candidates.csv` - exact 100 manifest rows selected for this batch.
- `csv/live_rows_expired.csv` - rows verified expired in live storage.
- `csv/skipped_before_selection_sample.csv` - sample of manifest rows skipped before selection.
- `live_cleanup_metadata.json` - machine-readable cleanup metadata and counts.
- `sql_templates/DO_NOT_RUN_rollback_status_only_expiry_100_batch2.sql` - row-id rollback template; backup restore remains preferred for full rollback.
