# Memory Interticker Contamination Manifest

Lane: Memory
Branch: preserve/dirty-work-20260430T065748Z
Worktree: /mnt/hdd-data/home/l4nd0/tenn
Execution mode: AUDIT MODE
Contested surfaces touched: none
Collision risk: MEDIUM for report generation; HIGH for live cleanup or DB mutation
Decision: audit only

## Contract Position

Target layer: Storage and Retrieval-adjacent Memory.
Relevant rules: SYSTEM_CONTRACT.md sections 1.1, 1.2, 1.3, 2.1, 2.2, and data/source integrity rules in 3-4.
Must not change: live memory rows, canonical financial truth, market/user/session memory boundaries, Qdrant, retrieval ranking, answer synthesis, source labels, or production routing.
Why safe: this report reads the company-memory SQLite store using an immutable read-only connection and writes CSV/JSON report artifacts only.
GPU process check required: no; this task does not spawn, restart, or depend on llama-server.

## Source Store

- Live API path observed in audit: `/data/reports/research_memory/company_memory.sqlite`
- Local inspected store: `/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/data/reports/research_memory/company_memory.sqlite`
- Store checksum: `72a33bb11ee537ddbd6e7ed3c03d279c57f8fe2dba61f677e574972e150d6e1b`
- Status counts: `{'expired': 250, 'active': 2083}`

## Current Manifest Counts

| item | count |
|---|---:|
| total rows | 2333 |
| active rows | 2083 |
| expired rows | 250 |
| distinct companies | 146 |
| active duplicate clusters | 94 |
| active duplicate rows in those clusters | 1615 |
| approval-required status-expire candidates | 963 |
| new/unclassified active duplicate rows | 652 |
| prior expire candidates still active | 963 |
| prior approved rows already expired | 249 |

## Files

- `csv/active_duplicate_clusters.csv` - active same-statement/source clusters crossing more than one company id.
- `csv/active_duplicate_rows_manifest.csv` - row-level manifest for every active row in those clusters.
- `csv/approval_required_status_expire_candidates.csv` - subset that still matches the prior high-confidence expiry manifest and remains active.
- `csv/manual_review_rows.csv` - review-only rows that should not be auto-expired from this report.
- `manifest_summary.json` - machine-readable counts and checksums.

## Cleanup Gate

No cleanup was executed. The only rows this report marks as mechanically plausible for a future status-only expiry are the rows in `approval_required_status_expire_candidates.csv`, and they still require explicit operator approval, a backup/checksum, a maximum row count, and active-job coordination before mutation.
