# Frame

## Objective
Fix the host-global Codex Stop hook so completed handoff / terminal goal state does not keep producing repeated dirty-warning loops.

## Why This Matters
Repeated Stop-hook warnings after a terminal handoff cause Codex to keep responding and burn tokens without useful work.

## Non-Negotiables
- Host-local Codex hook fix only.
- Do not touch Tenn product/runtime/data/extraction files.
- Do not touch the count-24 packet.
- Do not mutate GitHub, commit, push, delete branches/worktrees, run broad tests, start services, or launch auto-progress/cleanup work.

## Judgement Rules
- Preserve normal non-terminal dirty warnings.
- Suppress only repeated identical warnings when terminal/handoff-complete state is detected.
- Validate with a temp-repo self-check, not Tenn runtime tests.

## Scope In
- `/home/l4nd0/.codex/hooks/stop_check.py`
- Report bundle under `reports/agent_jobs/host_stop_hook_terminal_loop_fix_v1_20260613/`
- Task card `docs/agent_tasks/host_stop_hook_terminal_loop_fix_v1_20260613.md`

## Scope Out
- Tenn source/product/runtime/data/extraction files and all cleanup/commit/GitHub work.

## Evidence Sources
- Current repo state on `safe/cockpit-news-context-date-filter-merge-packets-preserve-v1-20260609` at `9dfa0f83cc09bf2e9edf40f659e0e2fdce0fa374`.
- Previous report `reports/agent_jobs/goal_monitor_stop_loop_audit_v1_20260613/`.
- Host hook `/home/l4nd0/.codex/hooks/stop_check.py`.

## Success Shape
- First useful dirty warning still appears.
- Repeated identical terminal/handoff dirty warning returns `{}`.
- Non-terminal repeated warnings still appear.
- Report explains verification and boundaries.

## Stop States
- `DONE_WITH_RISK` if host hook is patched and focused self-check passes but repo check-diff remains blocked by pre-existing unrelated dirt.
- `WAITING_ON_USER` if host hook edit is unsafe.

## Steering Log
- 2026-06-14 20:00 Australia/Melbourne - User explicitly approved host-global stop hook fix and forbade product/runtime/data/extraction, GitHub, commit, broad tests, cleanup, and count-24 mutation.
