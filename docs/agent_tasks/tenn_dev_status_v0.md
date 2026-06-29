---
job_id: tenn_dev_status_v0
lane: Reporting
supporting_lanes:
  - Repo Hygiene
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 1800
output_dir: reports/agent_jobs/tenn_dev_status_v0
mutation_mode: safe_extension
production_data_access: false
task_scope: control_plane_only
closeout_scope: control_plane_only
allowed_files:
  - docs/agent_tasks/tenn_dev_status_v0.md
  - scripts/tenn_dev_status.py
---

# Tenn Dev Status V0

## Objective

Add a small repo-native development status command that reduces day-to-day
agent workflow friction by printing the current Tenn repo state and the next
safe action.

## Scope

Allowed:

- Add `scripts/tenn_dev_status.py`.
- Add this task card.
- Run read-only git and Tenn guard checks.
- Run Python syntax validation and the new command.
- After explicit owner approval, publish this exact two-file change as a PR and
  merge only when live GitHub checks and merge-state evidence are safe.

Forbidden:

- Product, runtime, data, extraction, DB, Qdrant, news, memory, source-PDF,
  gold-label, prompt, service, dependency, GitHub, branch, worktree, or
  registry mutation.
- Dependency installation.
- Unapproved commit, push, PR creation, GitHub writes, branch deletion, worktree
  deletion, service starts, resets, stashes, or cleanups.
- Editing unrelated dirty files.

## Required Behavior

`python3 scripts/tenn_dev_status.py` prints a compact status report containing:

- repo root;
- current branch;
- HEAD;
- git status summary;
- whether untracked files exist;
- whether ignored report bundles exist under `reports/agent_jobs`;
- whether `tenn-git-guard` is available;
- safe read-only guard preflight summary when available;
- state classification: `CLEAN`, `DIRTY`, `REPORT_ONLY_OK`, `STALE_PATH`, or
  `BLOCKED`;
- `NEXT_SAFE_ACTION`.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/tenn_dev_status_v0.md`
- `python3 -m py_compile scripts/tenn_dev_status.py`
- `python3 scripts/tenn_dev_status.py`
- `git status --short --untracked-files=all`

## Closeout Notes

If unrelated dirty state exists, report it explicitly and do not absorb it into
this task.
