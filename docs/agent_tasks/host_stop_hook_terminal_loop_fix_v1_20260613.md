---
job_id: host_stop_hook_terminal_loop_fix_v1_20260613
lane: Evaluation
supporting_lanes:
  - Repo Hygiene
  - Reporting
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/host_stop_hook_terminal_loop_fix_v1_20260613
mutation_mode: safe_extension
production_data_access: false
allowed_files:
  - docs/agent_tasks/host_stop_hook_terminal_loop_fix_v1_20260613.md
  - reports/agent_jobs/host_stop_hook_terminal_loop_fix_v1_20260613/README.md
  - reports/agent_jobs/host_stop_hook_terminal_loop_fix_v1_20260613/FRAME.md
  - reports/agent_jobs/host_stop_hook_terminal_loop_fix_v1_20260613/STATE.md
  - reports/agent_jobs/host_stop_hook_terminal_loop_fix_v1_20260613/OPERATOR_NOTES.md
  - reports/agent_jobs/host_stop_hook_terminal_loop_fix_v1_20260613/IMPLEMENTATION_NOTES.md
  - reports/agent_jobs/host_stop_hook_terminal_loop_fix_v1_20260613/VALIDATION.md
  - reports/agent_jobs/host_stop_hook_terminal_loop_fix_v1_20260613/HOST_GLOBAL_STOP_HOOK_EVIDENCE.md
  - reports/agent_jobs/host_stop_hook_terminal_loop_fix_v1_20260613/stop_check_self_check.py
---

# Host Stop Hook Terminal Loop Fix V1

## Objective

Patch the host-global Codex Stop hook at
`/home/l4nd0/.codex/hooks/stop_check.py` so completed handoff / terminal goal
state does not keep producing repeated dirty milestone warning loops.

## Scope

Allowed:

- Inspect and patch `/home/l4nd0/.codex/hooks/stop_check.py`.
- Create report-local artifacts under the configured `output_dir`.
- Create a tiny report-local self-check script for the host hook behavior.
- Run focused host-hook self-checks only.

Forbidden:

- Tenn product, runtime, data, extraction, source-PDF, gold-label, prompt, DB,
  Qdrant, Redis, news, memory, service, model/GPU, backfill, or production-data
  mutation.
- Count-24 packet changes.
- GitHub mutation, commit, push, merge, rebase, cherry-pick, reset, stash,
  clean, branch deletion, or worktree deletion.
- Broad tests, auto-progress, cleanup, service starts, or runtime work.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/host_stop_hook_terminal_loop_fix_v1_20260613.md`
- Focused self-check proving first dirty warning appears, terminal repeated
  warning is suppressed, and non-terminal warnings still appear.
- `python3 -m py_compile /home/l4nd0/.codex/hooks/stop_check.py`
- `git diff --check`
- Changed-path guard proving repo changes are report/task-card only, aside from
  pre-existing unrelated dirt.
