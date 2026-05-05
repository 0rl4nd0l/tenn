# Summary

Lane: Memory
Execution mode: SAFE EXTENSION MODE
Approval: `approved_by_user_20260505_first_batch_249`

## Result

- Live cleanup executed: yes.
- Approved manifest: `reports/memory_historical_cleanup_dry_run_20260505_172806/csv/operator_first_batch_candidates.csv`
- Approved rows: 249.
- Rows expired: 249.
- Rows skipped: 0.
- Audit rows inserted: 249.
- Company summary scopes refreshed: 57.
- Status counts before: `active=1997`, `expired=1`.
- Status counts after: `active=1748`, `expired=250`.

## Storage Evidence

- Live DB: `financial-engine_v2/data/reports/research_memory/company_memory.sqlite`
- Pre-live checksum: `aa25e14894be56d601ce4ec9b4fd48e67eaf94b6cf60db13eae52c00c90ba5b1`
- Backup checksum: `aa25e14894be56d601ce4ec9b4fd48e67eaf94b6cf60db13eae52c00c90ba5b1`
- External rollback backup: `/mnt/sdb2/home/l4nd0/tenn_runtime_backups/memory_cleanup_20260505_174752/live_expiry_backup/company_memory.sqlite.pre_live_expiry_20260505_174752`
- Post-live checksum after WAL checkpoint: `62fbc2b01a6b0fb2ba50ba09fdb6ba493f1cbcef9021bdf3d9e1cc196a5b7ff1`
- Market memory checksum unchanged: `2a1d8cc4434a4f924345939efba966609bee502eaa01cc2f92f6239d9973f9ea`
- Thesis memory checksum unchanged: `5d23a987d9e6fb249852e617c78b50374cfbe65ab45741669d8635e6d8ee0f94`

## Scope

The live mutation changed approved `memory_entries.status` values to `expired`, inserted `change_log` audit rows, and refreshed `company_memory.active_entry_count` summaries for affected companies. It did not delete rows, rewrite text, canonicalize aliases, rehome market/macro rows, touch market/thesis/session stores, reindex Qdrant, run ingestion, change retrieval/ranking, change source labels, or change financial truth.
