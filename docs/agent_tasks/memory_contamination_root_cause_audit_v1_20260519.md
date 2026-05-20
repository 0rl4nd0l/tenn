---
job_id: memory_contamination_root_cause_audit_v1_20260519
lane: Memory
owner: Codex
allowed_files:
  - docs/agent_tasks/memory_contamination_root_cause_audit_v1_20260519.md
  - reports/agent_jobs/memory_contamination_root_cause_audit_v1_20260519/
approval_required: false
allow_audit_code_changes: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/memory_contamination_root_cause_audit_v1_20260519
mutation_mode: audit_only
production_data_access: false
---

# Task

Complete Memory Contamination Root Cause v1 read-only audit for Tenn.

Primary lane: Memory. Supporting lanes: Evaluation, Provenance, Query Orchestration.

# Objective

Prove the root cause and blast radius of Tenn company-memory contamination / memo-level ticker fanout without mutating production data. Produce a complete report that explains whether contaminated rows can surface in ticker-specific chat/company-analysis contexts, which writer/path caused fanout if provable, what tests would prevent recurrence, and what cleanup plan would be safe later only after approval.

# Required questions

1. What memory stores exist in this checkout?
2. Which store(s) contain company memory rows?
3. What schema/fields identify entity, ticker, source memo, source id, document id, batch id, writer path, row scope, statement text, created_at, and provenance?
4. Is contamination visible in the current accessible memory artifacts?
5. Can duplicate/fanout clusters be traced back to a shared memo/source/batch?
6. Which writer function or ingest path likely caused fanout?
7. Is the root cause already fixed by a guard in current code, or is it still open?
8. Can contaminated rows surface in ticker-specific chat/company-analysis contexts?
9. What synthetic fixture would reproduce the bug without touching live memory?
10. What cleanup plan is safe later, after approval, and what must not be done yet?

# Required preflight

Run and report:

- `pwd`
- `readlink -f /home/l4nd0/tenn-runtime`
- `git branch --show-current`
- `git rev-parse --short=12 HEAD`
- `git status --short`
- `git worktree list`
- `git show --stat --oneline --no-renames HEAD`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/memory_contamination_root_cause_audit_v1_20260519.md`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/memory_contamination_root_cause_audit_v1_20260519.md`
- Claim only if safe. If overlap is blocked only by unrelated dirty task cards and no active Memory job overlaps, continue report-only and explain why.

# Inspect read-only

Search and inspect relevant files only:

- `financial-engine_v2/backend/app/`
- `financial-engine_v2/backend/app/services/`
- `financial-engine_v2/backend/app/routes/`
- `financial-engine_v2/backend/tests/`
- `financial-engine_v2/cockpit/`
- `financial-engine_v2/data/`
- `scripts/`
- `docs/`
- `reports/agent_jobs/*memory*`
- `reports/agent_jobs/*contamination*`
- `reports/agent_jobs/*interticker*`
- `reports/agent_jobs/*fanout*`
- `reports/agent_jobs/*signal*`
- `reports/agent_jobs/*company_memory*`
- `reports/agent_jobs/*research_memory*`
- SQLite schemas, JSONL stores, memory snapshots, or report artifacts related to company memory.

# Search terms

- `company_memory`
- `company memory`
- `market_memory`
- `thesis_memory`
- `memory_scope`
- `entity_scope`
- `ticker_scope`
- `source_memo`
- `memo_id`
- `source_id`
- `fanout`
- `contamination`
- `duplicate`
- `interticker`
- `write_memory`
- `save_memory`
- `memory_writer`
- `MemoryStore`
- `research_memory`
- `entity_alias`
- `ticker_identity`
- `canonical_ticker`
- `company analysis`
- `all data we have`
- `local memory`
- `memory_context`
- `source:memory`
- `contaminated`
- `cleanup`
- `batch`
- `provenance`
- `source_labels`
- `row_hash`
- `duplicate_cluster`

# Data access rules

Allowed:

- Prefer report artifacts, fixtures, schema files, and tests.
- Inspect local files read-only when they are already in repo/worktree and do not require mutating production services.
- Write only audit artifacts under this task card's allowed paths.

Forbidden:

- Do not delete, update, expire, move, canonicalize, rewrite, reindex, resync, migrate, backfill, or mutate memory, DBs, Qdrant, news stores, company memory, market memory, thesis memory, financial truth, parser/extraction outputs, or runtime config.
- Do not broadly open or dump sensitive personal data.
- Do not access live SQLite/DB production memory unless separately approved. If needed, report `DATA_MISSING` and document the exact path/table/query required.

# Required output

Write:

`reports/agent_jobs/memory_contamination_root_cause_audit_v1_20260519/README.md`

Include:

- Executive verdict
- Confirmed facts
- Inferred facts
- Speculative claims
- `DATA_MISSING`
- Memory store inventory
- Writer path trace
- Reader/surfacing path trace
- Fanout/blast-radius assessment
- Prevention plan
- Cleanup plan later
- Hard stops / do-not-do
- Validation commands run
- Final git status
- Registry release status if claimed
- Project Memory save recommendation

# Hard boundaries

Do not:

- clean up memory now
- canonicalize aliases now
- rewrite memory now
- reindex Qdrant now
- resync news now
- touch runtime services
- touch financial truth
- touch parser/extraction
- touch Cockpit chat guard patch
- touch Home producers
- touch runtime/model/GPU config
- commit, stash, clean, or run destructive commands
