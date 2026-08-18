---
job_id: full_system_local_repo_system_audit_v1_20260525
lane: Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/full_system_local_repo_system_audit_v1_20260525.md
  - reports/agent_jobs/full_system_local_repo_system_audit_v1_20260525/**
approval_required: false
timeout_seconds: 10800
output_dir: reports/agent_jobs/full_system_local_repo_system_audit_v1_20260525
mutation_mode: audit_only
production_data_access: false
---

# Task

Run an audit-only local repo/system stocktake for Tenn. The goal is to produce a complete evidence pack for GPT, not to implement changes.

# Hard boundaries

Do not edit, format, stage, commit, revert, delete, move, clean, migrate, reindex, resync, relabel, or reroute anything outside this task card and report output directory.

Forbidden mutation surfaces:

- production DBs
- Qdrant
- news.sqlite or news stores
- embeddings
- company memory
- market memory
- thesis memory
- holdings/local personal state
- feedback stores
- canonical financial truth
- parser routing
- extraction prompts
- gold labels
- canonical writes
- runtime/model/GPU/service binding
- Cockpit source-label UI changes
- backend route behavior
- frontend implementation
- ingestion/backfill/sync jobs
- migrations
- destructive git commands
- unrelated dirty files

Do not run:

- ingestion jobs
- extraction jobs over production corpus
- Qdrant sync/reindex
- DB migrations
- news backfills
- memory cleanup
- parser comparator runs that write outside output_dir
- browser automation that changes state
- broad test suites if they may mutate local data
- package installs
- git add/commit/push/checkout/restore/reset/clean/stash

Allowed writes:

- docs/agent_tasks/full_system_local_repo_system_audit_v1_20260525.md
- reports/agent_jobs/full_system_local_repo_system_audit_v1_20260525/**

Allowed read-only inspection:

- repo files
- docs
- task cards
- agent reports
- validation artifacts
- test files
- config files
- Git metadata
- local branches/worktrees
- GitHub CLI read-only status if available and already authenticated
- service/process/port metadata only, no state-changing calls
- data directory file inventory/counts/paths only, not content queries, unless the files are explicitly report artifacts

# Required outputs

- reports/agent_jobs/full_system_local_repo_system_audit_v1_20260525/README.md
- reports/agent_jobs/full_system_local_repo_system_audit_v1_20260525/status.json
- reports/agent_jobs/full_system_local_repo_system_audit_v1_20260525/repo_state.json
- reports/agent_jobs/full_system_local_repo_system_audit_v1_20260525/current_state_reconstruction.md
- reports/agent_jobs/full_system_local_repo_system_audit_v1_20260525/system_map.md
- reports/agent_jobs/full_system_local_repo_system_audit_v1_20260525/lane_audit.md
- reports/agent_jobs/full_system_local_repo_system_audit_v1_20260525/user_workflow_audit.md
- reports/agent_jobs/full_system_local_repo_system_audit_v1_20260525/trust_provenance_evaluation_plan.md
- reports/agent_jobs/full_system_local_repo_system_audit_v1_20260525/performance_runtime_audit.md
- reports/agent_jobs/full_system_local_repo_system_audit_v1_20260525/repo_dev_agent_audit.md
- reports/agent_jobs/full_system_local_repo_system_audit_v1_20260525/recommended_next_tasks.md
- reports/agent_jobs/full_system_local_repo_system_audit_v1_20260525/diff-check.json

# Validation

Run safe validation only:

- python3 -m json.tool reports/agent_jobs/full_system_local_repo_system_audit_v1_20260525/status.json
- python3 -m json.tool reports/agent_jobs/full_system_local_repo_system_audit_v1_20260525/repo_state.json
- git diff --check
- python3 scripts/agent_job_contract.py validate docs/agent_tasks/full_system_local_repo_system_audit_v1_20260525.md, if present
- python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/full_system_local_repo_system_audit_v1_20260525.md, if present
