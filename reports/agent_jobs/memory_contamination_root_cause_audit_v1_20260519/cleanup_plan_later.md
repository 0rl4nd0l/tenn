# Cleanup Plan Later

No cleanup is approved or safe in this task.

## Approval-Gated Steps

1. Create a new task card with `production_data_access=true` for read-only inventory only.
2. Take or verify a backup/export of `company_memory.sqlite`, WAL/SHM if present, `change_log`, memo JSONL files, and source registry files.
3. Open the DB read-only and immutable where possible.
4. Generate a row-ID manifest of active duplicate statement clusters and active source-fanout clusters.
5. Classify candidate rows into:
   - preserve target-specific rows;
   - status-expire candidate after approval;
   - manual review;
   - alias merge later;
   - market/macro rehome later;
   - blocked/do not touch.
6. Require operator review for all candidate rows that lack explicit target-company evidence or source spans.
7. Only after explicit mutation approval, run a capped status-only expiry batch through backend-owned API or backend-owned maintenance process.
8. Write change-log/audit artifacts for every changed row.
9. Verify with read-only active-cluster audit and ticker-sampled company_dump checks.
10. Preserve rollback SQL or restore instructions tied to the backup checksum.

## Must Not Do

- Do not delete rows.
- Do not rewrite statements.
- Do not rewrite company IDs.
- Do not canonicalize aliases in place.
- Do not reindex Qdrant.
- Do not resync news or commentary.
- Do not use LLM output as cleanup authority.
- Do not hide contamination by retrieval/ranking changes.

## Safe First Cleanup Shape, If Approved

Use status-only expiry for high-confidence duplicate fanout rows where:

- the same `normalized_statement + source_id` appears under multiple company IDs;
- the statement explicitly names a different target company;
- at least one target-specific row is preserved;
- the row ID is present in an approved manifest;
- the operation is capped by max row count and backup checksum.
