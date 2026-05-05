# Next Codex Prompt: Live Cleanup Request

Use only after operator approval.

```text
You are Codex working on Tenn.

TASK
Memory Historical Cleanup Live Expiry Batch 1.

LANE
Memory

EXECUTION MODE
SAFE EXTENSION MODE, live DB mutation authorized only for the approved row ids in:
reports/memory_historical_cleanup_dry_run_20260505_172806/csv/operator_first_batch_candidates.csv

HARD REQUIREMENTS
- Read SYSTEM_CONTRACT.md, AGENTS.md, docs/architecture/18_cockpit_memory.md, and docs/architecture/22_memory_ownership_map.md.
- Confirm branch/worktree and collision status.
- Confirm live DB path is financial-engine_v2/data/reports/research_memory/company_memory.sqlite.
- Stop immediately if path ambiguity exists.
- Create backup snapshot of company DB and any WAL/SHM files.
- Record checksums before mutation.
- Expire only the approved first-batch row ids.
- Use status-only expiry plus audit rows unless operator explicitly approves the current API timestamp mutation semantics.
- Do not delete, rewrite text, canonicalize aliases, rehome market/macro rows, change retrieval/ranking, change source labels, reindex Qdrant, or run ingestion.
- Validate row counts and rollback readiness.
- Commit only report artifacts and approved cleanup manifest.
```
