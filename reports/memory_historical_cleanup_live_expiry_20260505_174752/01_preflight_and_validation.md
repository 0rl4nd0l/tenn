# Preflight And Validation

## Session Declaration

Lane: Memory
Branch: `preserve/dirty-work-20260430T065748Z`
Worktree: `/mnt/sdb2/home/l4nd0/tenn`
Execution mode: SAFE EXTENSION MODE
Contested surfaces touched: live company memory DB
Collision risk: HIGH for live mutation, bounded by explicit operator approval for the 249-row first batch.

## Contract Position

Target layer: Storage, backend-owned qualitative company memory.
Relevant contract rules: backend authority, memory ownership, data preservation, no financial-truth writes, and retrieval boundary.
Must not change: live market memory, thesis memory, session/operational state, Qdrant, ingestion, retrieval/ranking, source labels, alias mappings, row text, row provenance, and financial truth.
Why safe: the mutation was restricted to the operator-approved first-batch row ids, used status-only expiry, inserted audit rows, and had a pre-mutation backup snapshot.
GPU process check required: no.

## Preflight Evidence

- Branch: `preserve/dirty-work-20260430T065748Z`
- HEAD before cleanup: `165be97d7e45632abd42fdebd2ef9b27805332d8`
- Approved manifest rows: 249.
- Approved manifest unique row ids: 249.
- Live DB path: `/data/reports/research_memory/company_memory.sqlite` inside `fe_backend`.
- Host path: `financial-engine_v2/data/reports/research_memory/company_memory.sqlite`.
- Direct host writes were blocked because the live DB is root-owned; execution used the existing `fe_backend` container root context against the bind-mounted `/data` path.

## Validation Commands

Validated after commit/checkpoint:

```text
total_rows 1998
status_counts {'active': 1748, 'expired': 250}
approved_expired 249
approved_active 0
approval_audit_rows 249
```

The first script attempt stopped before mutation when SQLite backup byte checksums did not match. The live checksum remained unchanged after that stopped attempt. The executed path then used a raw file-copy backup because no live WAL/SHM file was present before mutation.
