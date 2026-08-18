# Goal Monitor Stop Loop Audit V1

Status: DONE_WITH_RISK

## Objective

Audit and repair Tenn goal-monitor / stop-state behavior so completed goals do not keep looping and wasting tokens.

## Current Verdict

`DONE_WITH_RISK`.

The repo has a real Stop hook, but it is a task-card contract hook, not a goal-terminal monitor. The host has a real goal monitor and token-burn guard, but they are warning-first and do not enforce handoff terminal state.

The exact failure is best explained by Stop-hook warning output after a terminal handoff. Current evidence shows the host-global Stop hook repeatedly emits dirty milestone warnings and has no de-duplication or handoff-complete guard.

## Minimal Fix Implemented

Repo-local `scripts/agent_job_hook.py` now returns `{}` for successful Codex `Stop` checks. A passing Stop hook should be quiet; only real contract failures should add blocking context.

## Files Touched

- `docs/agent_tasks/goal_monitor_stop_loop_audit_v1_20260613.md`
- `scripts/agent_job_hook.py`
- `scripts/test_agent_job_hook.py`
- `reports/agent_jobs/goal_monitor_stop_loop_audit_v1_20260613/*`

## Files Intentionally Not Touched

- `docs/agent_tasks/extraction_count24_approval_packet_current_canonical_v1_20260609.md`
- Host-global `~/.codex/hooks/stop_check.py`
- Product/runtime/data/extraction/greyhound files
- DB, Qdrant, news, memory, source PDFs, gold labels, prompts, services, model/GPU config
- GitHub, branches, worktrees, commits

## Report Index

- `FAILURE_RECONSTRUCTION.md`
- `CURRENT_GOAL_MONITOR_SURFACE.md`
- `STOP_HOOK_AUDIT.md`
- `GAP_ANALYSIS.md`
- `FIX_PLAN.md`
- `IMPLEMENTATION_NOTES.md`
- `VALIDATION.md`
- `FRAME.md`
- `STATE.md`
- `OPERATOR_NOTES.md`

## Unsafe Actions Avoided

No services started, no broad tests, no product/runtime/data/extraction mutation, no greyhound prediction work, no GitHub mutation, no destructive Git, no count-24 change.

## Remaining Risk

The likely repeated dirty warning source is host-global `~/.codex/hooks/stop_check.py`, which is outside this repo task-card allowlist and remains unpatched.

Focused pytest could not run because `pytest` is unavailable in the current Python and `uv run` environments. Syntax checks and synthetic hook self-checks passed.

## Next Recommended Prompt

Approve a separate host-control-plane patch for `/home/l4nd0/.codex/hooks/stop_check.py` using the bounded prompt in `FIX_PLAN.md`.
