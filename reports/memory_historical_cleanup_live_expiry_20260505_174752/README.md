# Live Memory Expiry First Batch

Lane: Memory
Execution mode: SAFE EXTENSION MODE
Approval: approved_by_user_20260505_first_batch_249
Approved manifest: `/workspace/reports/memory_historical_cleanup_dry_run_20260505_172806/csv/operator_first_batch_candidates.csv`
Live DB: `/data/reports/research_memory/company_memory.sqlite`

## Result

- Approved rows: 249
- Rows expired: 249
- Rows skipped: 0
- Audit rows inserted: 249
- Status counts before: {'active': 1997, 'expired': 1}
- Status counts after: {'active': 1748, 'expired': 250}
- Backup path: `/workspace/reports/memory_historical_cleanup_live_expiry_20260505_174752/backup/company_memory.sqlite.pre_live_expiry_20260505_174752`
- Backup checksum: `aa25e14894be56d601ce4ec9b4fd48e67eaf94b6cf60db13eae52c00c90ba5b1`
- Backup method: `raw_file_copy`
- Live checksum before: `aa25e14894be56d601ce4ec9b4fd48e67eaf94b6cf60db13eae52c00c90ba5b1`
- Live checksum after checkpoint: `62fbc2b01a6b0fb2ba50ba09fdb6ba493f1cbcef9021bdf3d9e1cc196a5b7ff1`
- Live checksum immediately after commit before checkpoint: `aa25e14894be56d601ce4ec9b4fd48e67eaf94b6cf60db13eae52c00c90ba5b1`

## Scope

The live mutation changed only approved `memory_entries.status` values, inserted `change_log` audit rows, and refreshed `company_memory.active_entry_count` summaries for affected companies. It did not delete rows, rewrite text, canonicalize aliases, rehome market/macro rows, touch market/thesis/session stores, reindex Qdrant, run ingestion, change retrieval/ranking, or change financial truth.
