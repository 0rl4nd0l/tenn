---
job_id: git_hook_install_execution_v1_20260616
lane: Reporting
supporting_lanes:
  - Repo Hygiene
owner: Codex
approval_required: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/git_hook_install_execution_v1_20260616
mutation_mode: safe_extension
production_data_access: false
allowed_files:
  - docs/agent_tasks/git_hook_install_execution_v1_20260616.md
  - .githooks/pre-commit
  - .githooks/pre-push
  - scripts/check_agent_hooks.py
  - scripts/test_check_agent_hooks.py
  - reports/agent_jobs/git_hook_install_execution_v1_20260616/REPORT.md
  - reports/agent_jobs/git_hook_install_execution_v1_20260616/COMMANDS.md
---

# Git Hook Install Execution V1

## Objective

Apply the approved Git hook repair from
`reports/agent_jobs/git_hook_install_plan_v1_20260616/PLAN.md`.

## Scope

Allowed:

- Create root-level versioned `.githooks/pre-commit` and `.githooks/pre-push`.
- Set local Git config `core.hooksPath` to `.githooks`.
- Patch `scripts/check_agent_hooks.py` so its effective hook directory comes
  from `git rev-parse --git-path hooks`.
- Add or adjust focused checker tests only.
- Write execution report artifacts.

Forbidden:

- Runtime/service starts, dependency installs, data mutation, GitHub writes,
  commits, branch operations, reset, stash, clean, worktree deletion, broad
  formatting, or touching files outside `allowed_files`.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/git_hook_install_execution_v1_20260616.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/check_agent_hooks.py --repo-root . --strict --expect-fingerprint 'pre-commit=git rev-parse --show-toplevel' --expect-fingerprint 'pre-push=git rev-parse --show-toplevel'`
- `financial-engine_v2/.venv/bin/pytest -q scripts/test_check_agent_hooks.py`
- `git config --show-origin --get core.hooksPath`
- `git rev-parse --git-path hooks`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/git_hook_install_execution_v1_20260616.md --repo-root . --no-write-report`
