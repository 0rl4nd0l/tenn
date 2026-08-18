---
job_id: status_route_contract_implementation_for_news_health_v1_20260525
lane: Query Orchestration
supporting_lanes:
  - Provenance
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/status_route_contract_implementation_for_news_health_v1_20260525.md
  - reports/agent_jobs/status_route_contract_implementation_for_news_health_v1_20260525/README.md
  - reports/agent_jobs/status_route_contract_implementation_for_news_health_v1_20260525/status.json
  - reports/agent_jobs/status_route_contract_implementation_for_news_health_v1_20260525/status_route_contract_audit.json
  - reports/agent_jobs/status_route_contract_implementation_for_news_health_v1_20260525/status_reporting_gap_register.json
  - reports/agent_jobs/status_route_contract_implementation_for_news_health_v1_20260525/validation.json
  - reports/agent_jobs/status_route_contract_implementation_for_news_health_v1_20260525/diff-check.json
  - financial-engine_v2/backend/app/services/news_health_status.py
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/tests/test_cockpit_news_status.py
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 10800
output_dir: reports/agent_jobs/status_route_contract_implementation_for_news_health_v1_20260525
mutation_mode: safe_extension
production_data_access: false
---

# Status Route Contract Implementation For News Health

Audit first, then implement only if exact candidate source and test files are
bounded, registry overlap permits, and the change remains a status/reporting
contract extension. Initial allowed writes are limited to this task card and the
listed report artifacts.

Primary lane: Query Orchestration.

Supporting lanes:

- Provenance
- Reporting

## Objective

Implement, or precisely audit if implementation is unsafe, the missing
news/A2M health status-route contract so Tenn reports the split A2M truth:
Qdrant-backed retrieval works, canonical NVMe SQLite projection is missing,
legacy SQLite has evidence but is not the current consumer, Cockpit query route
works via `/rag/query`, Cockpit/news status routes are missing or incomplete,
chat synthesis remains `DATA_MISSING`, and projection repair has not run.

## Initial Risk

- LOW for report/status contract audit.
- MEDIUM for bounded backend/Cockpit status-route implementation or tests.
- HIGH for DB/Qdrant/news-store mutation, projection rebuild,
  ingestion/resync/reindex/backfill, route behavior changes that alter
  retrieval data flow, chat/session writes, source-label changes, or alias
  hacks.

## Current Known A2M Status To Preserve

- `qdrant_retrieval = ok`
- `canonical_sqlite_projection = missing`
- `legacy_sqlite_projection = evidence_present_not_current_consumer`
- `cockpit_query_route = ok_via_rag_query`
- `cockpit_status_routes = missing_404`
- `chat_synthesis = DATA_MISSING`
- `projection_repair = not_run`

Do not report `A2M missing`, `A2M projection fixed`, `legacy SQLite is
canonical`, or `chat synthesis proven`.

## Required Preflight

1. Print pwd, hostname, date, branch, HEAD, and recent commits.
2. Run `git status --short --untracked-files=all`.
3. Run `git worktree list`.
4. Verify task-card, registry, and check-diff command syntax from repo docs/help
   before relying on exact commands.
5. Validate this task card.
6. Run registry/list-active if available.
7. Run registry/check-overlap for this task card if available.
8. Classify active jobs and foreign untracked task cards. Do not clean, delete,
   stash, reset, move, overwrite, or commit foreign work.
9. If blockers appear, attempt safe isolation first.
10. Stop only if safe isolation is impossible or required changes touch
    forbidden surfaces.

## Phase 1 Audit

Write
`reports/agent_jobs/status_route_contract_implementation_for_news_health_v1_20260525/status_route_contract_audit.json`
with discovered routes, missing routes, current consumers, candidate
implementation files, candidate tests, overlap/risk, and decision:
`implement`, `report-only`, or `blocked`.

## Phase 2 Safe Extension Gate

Phase 1 discovered the exact implementation files now listed in
`allowed_files`. Before source or test edits, re-run validation and
registry/check-overlap. Proceed only if changes are limited to status/reporting
contract and focused tests.

Allowed implementation classes:

- Add a read-only backend/Cockpit status endpoint or status field that reports
  known health categories without changing retrieval or data flow.
- Add a status/reporting helper that classifies Qdrant retrieval versus
  canonical SQLite projection versus legacy SQLite evidence versus chat
  `DATA_MISSING`.
- Add focused tests for the status contract using mocks or fixtures.
- Add report artifacts explaining the contract.

Forbidden implementation classes:

- No projection rebuild.
- No ingestion, backfill, reindex, resync, or news refresh.
- No Qdrant mutation.
- No SQLite, Postgres, DB, or news-store mutation.
- No copying legacy `/mnt/sdb2` DBs.
- No symlinking legacy DBs into canonical paths.
- No one-off A2M alias hacks.
- No ticker/company canonicalization changes.
- No source-label trust semantic changes.
- No parser, extraction, or metric scoring changes.
- No chat/session write smoke unless separately carded.
- No Docker, systemd, cron, env, runtime, model, or GPU changes.
- No broad Cockpit UI redesign.
- No cleanup of foreign task cards or worktrees.

## Required Outputs

- `reports/agent_jobs/status_route_contract_implementation_for_news_health_v1_20260525/README.md`
- `reports/agent_jobs/status_route_contract_implementation_for_news_health_v1_20260525/status.json`
- `reports/agent_jobs/status_route_contract_implementation_for_news_health_v1_20260525/status_route_contract_audit.json`
- `reports/agent_jobs/status_route_contract_implementation_for_news_health_v1_20260525/status_reporting_gap_register.json`
- `reports/agent_jobs/status_route_contract_implementation_for_news_health_v1_20260525/validation.json`
- `reports/agent_jobs/status_route_contract_implementation_for_news_health_v1_20260525/diff-check.json`

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/status_route_contract_implementation_for_news_health_v1_20260525.md`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/status_route_contract_implementation_for_news_health_v1_20260525.md`
- After any allowed-file update, repeat validation and check-overlap.
- Focused tests for any touched backend/Cockpit route/status files.
- TypeScript/eslint only if Cockpit files change.
- Python pytest/ruff/py_compile only if backend Python files change.
- JSON validation for generated artifacts.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/status_route_contract_implementation_for_news_health_v1_20260525.md`
- Final `git status --short --untracked-files=all`.
- Final `python3 scripts/agent_job_registry.py list-active`.
