---
job_id: registry_readonly_no_lock_list_active_v1_20260525
title: Registry read-only no-lock list-active mode v1
owner: Codex
lane: Reporting
primary_lane: Repo Hygiene
supporting_lanes:
  - Reporting
  - Evaluation
mutation_mode: safe_extension
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
production_data_access: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/registry_readonly_no_lock_list_active_v1_20260525
allowed_files:
  - scripts/agent_job_registry.py
  - scripts/test_agent_job_registry.py
  - docs/agent_tasks/registry_readonly_no_lock_list_active_v1_20260525.md
  - reports/agent_jobs/registry_readonly_no_lock_list_active_v1_20260525/README.md
  - reports/agent_jobs/registry_readonly_no_lock_list_active_v1_20260525/status.json
  - reports/agent_jobs/registry_readonly_no_lock_list_active_v1_20260525/validation.json
  - reports/agent_jobs/registry_readonly_no_lock_list_active_v1_20260525/diff-check.json
---

# Registry Read-only No-lock List-active Mode v1

## Objective

Resolve GitHub issue #80 by adding a true read-only registry status path so
automation and issue-management agents can inspect active Tenn jobs without
creating lock files or mutating shared registry state.

## Scope

- Add a minimal `list-active --read-only` path to `scripts/agent_job_registry.py`.
- Preserve existing `list-active`, `claim`, `heartbeat`, `release`, and
  `check-overlap` behavior unless validation proves a lock-safety bug.
- Add focused tests proving read-only listing does not create or mutate registry
  files and existing registry behavior still passes.
- Write closeout report artifacts under this task's report directory.

## Forbidden

- Product/backend/frontend/runtime code.
- DB, Qdrant, news, memory, or canonical financial truth mutation.
- Parser routing, extraction prompts, gold labels, model/runtime/GPU/service
  config changes.
- Branch cleanup, merge, rebase, reset, stash, prune, or delete.
- Unrelated dirty-file edits.
- Live GitHub issue closeout until validation passes.

## Validation

- `python3 scripts/agent_job_registry.py --help`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- Registry file mtime/content comparison before and after the read-only command.
- Focused registry tests proving read-only listing does not write/mutate
  registry files and existing list/claim/release behavior still works.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/registry_readonly_no_lock_list_active_v1_20260525.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/registry_readonly_no_lock_list_active_v1_20260525.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/registry_readonly_no_lock_list_active_v1_20260525.md --repo-root .`
- `git diff --check`
- JSON parse report artifacts.

## Hard Stops

- Stop if read-only status requires lock acquisition, heartbeat, release, prune,
  timestamp update, or registry writes.
- Stop if the implementation weakens lock safety for claim/release/write
  operations.
- Stop if validation requires product/runtime/data mutation.
