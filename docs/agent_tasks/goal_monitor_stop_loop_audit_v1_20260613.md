---
job_id: goal_monitor_stop_loop_audit_v1_20260613
lane: Evaluation
supporting_lanes:
  - Repo Hygiene
  - Reporting
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/goal_monitor_stop_loop_audit_v1_20260613
mutation_mode: safe_extension
production_data_access: false
allowed_files:
  - docs/agent_tasks/goal_monitor_stop_loop_audit_v1_20260613.md
  - scripts/agent_job_hook.py
  - scripts/test_agent_job_hook.py
  - reports/agent_jobs/goal_monitor_stop_loop_audit_v1_20260613/README.md
  - reports/agent_jobs/goal_monitor_stop_loop_audit_v1_20260613/FAILURE_RECONSTRUCTION.md
  - reports/agent_jobs/goal_monitor_stop_loop_audit_v1_20260613/CURRENT_GOAL_MONITOR_SURFACE.md
  - reports/agent_jobs/goal_monitor_stop_loop_audit_v1_20260613/STOP_HOOK_AUDIT.md
  - reports/agent_jobs/goal_monitor_stop_loop_audit_v1_20260613/GAP_ANALYSIS.md
  - reports/agent_jobs/goal_monitor_stop_loop_audit_v1_20260613/FIX_PLAN.md
  - reports/agent_jobs/goal_monitor_stop_loop_audit_v1_20260613/IMPLEMENTATION_NOTES.md
  - reports/agent_jobs/goal_monitor_stop_loop_audit_v1_20260613/VALIDATION.md
  - reports/agent_jobs/goal_monitor_stop_loop_audit_v1_20260613/FRAME.md
  - reports/agent_jobs/goal_monitor_stop_loop_audit_v1_20260613/STATE.md
  - reports/agent_jobs/goal_monitor_stop_loop_audit_v1_20260613/OPERATOR_NOTES.md
---

# Goal Monitor Stop Loop Audit V1

## Objective

Audit Tenn goal-monitor and stop-state behavior so completed handoffs do not
keep looping and wasting tokens. Implement one minimal control-plane fix if the
current hook surface allows a safe scoped change.

## Scope

Allowed:

- Inspect Tenn control-plane instructions, skills, task-card scripts, registry
  scripts, Codex hook configuration, stop-hook code, and current report-local
  artifacts.
- Read `/tmp/greyhound_accuracy_odds_closeout_20260613T0854.md` if available.
- Update `scripts/agent_job_hook.py` and its focused test file only if the fix
  remains control-plane-only.
- Write the required report bundle under `output_dir`.

Forbidden:

- Product, backend, frontend, runtime, data, extraction, source-PDF,
  gold-label, prompt, DB, Qdrant, Redis, news, memory, service, model/GPU,
  backfill, production-data, or live-service mutation.
- Count-24 extraction approval packet changes.
- Broad tests or service starts.
- GitHub mutation, commit, push, merge, rebase, cherry-pick, reset, stash,
  clean, branch deletion, or worktree deletion.

## Required Evidence

- `AGENTS.md`
- `.agents/skills/tenn-goal-report/SKILL.md`
- `.agents/skills/tenn-frame-design/SKILL.md`
- `.agents/skills/tenn-git-hygiene/SKILL.md`
- `.agents/skills/tenn-auto-progress/SKILL.md`
- `.codex/hooks.json`
- `.codex/config.toml`
- `scripts/agent_job_hook.py`
- `scripts/agent_job_registry.py`
- `scripts/agent_job_contract.py`
- Existing focused hook tests.
- Relevant report-local references to goal monitor, stop hook, handoff, terminal
  states, repeated stop, token loop, and no-tick-chasing.
- `/tmp/greyhound_accuracy_odds_closeout_20260613T0854.md` when present.

## Required Output

- `README.md`
- `FAILURE_RECONSTRUCTION.md`
- `CURRENT_GOAL_MONITOR_SURFACE.md`
- `STOP_HOOK_AUDIT.md`
- `GAP_ANALYSIS.md`
- `FIX_PLAN.md`
- `IMPLEMENTATION_NOTES.md`
- `VALIDATION.md`

Frame artifacts are allowed because this is a `/goal` run.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/goal_monitor_stop_loop_audit_v1_20260613.md`
- Focused hook tests relevant to any hook change.
- Focused hook self-checks with synthetic Stop payloads if useful.
- `git diff --check`
- Changed-path guard proving only allowed control-plane/report paths changed.
- Final `git status --short --untracked-files=all`.
