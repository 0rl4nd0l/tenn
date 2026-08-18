# Implementation Notes

## Host Hook Before

`/home/l4nd0/.codex/hooks/stop_check.py` previously:

- Hard-coded `REPO = "/home/l4nd0/tenn"`.
- Read dirty, staged, and untracked files.
- Emitted `MILESTONE NOT COMMITTED` every Stop while files stayed dirty.
- Had no terminal goal, handoff-complete, or repeated-warning guard.

## Host Hook After

The hook now:

- Resolves repo from `CODEX_STOP_CHECK_REPO`, hook payload cwd/root fields, current cwd, then legacy `/home/l4nd0/tenn`.
- Keeps the same dirty milestone, diff summary, and docs-coverage warning behavior.
- Adds informational wording: do not continue work unless the user asked for cleanup or commit.
- Detects terminal/handoff-complete state from:
  - `CODEX_STOP_CHECK_TERMINAL_HANDOFF`
  - `CODEX_STOP_CHECK_HANDOFF_COMPLETE`
  - `CODEX_STOP_CHECK_HANDOFF_PATH`
  - hook payload terminal/handoff keys
  - hook payload `goal.status`
  - `CODEX_THREAD_ID` status in `~/.codex/goals_1.sqlite`
- Stores a small terminal-warning fingerprint under `/tmp/codex-stop-check/` by thread/repo.
- Suppresses repeated identical terminal warnings by returning `{}`.
- Leaves non-terminal warnings unsuppressed.

## Self-Check

Added report-local `stop_check_self_check.py`. It creates a temp Git repo and isolated cache, then proves:

- First terminal dirty warning emits.
- Second identical terminal dirty warning suppresses.
- Non-terminal dirty warnings still emit on repeated Stop calls.

## Files Changed

- Host-global: `/home/l4nd0/.codex/hooks/stop_check.py`
- Repo report/task files:
  - `docs/agent_tasks/host_stop_hook_terminal_loop_fix_v1_20260613.md`
  - `reports/agent_jobs/host_stop_hook_terminal_loop_fix_v1_20260613/*`

## Files Intentionally Not Touched

- Tenn product/runtime/data/extraction files.
- `docs/agent_tasks/extraction_count24_approval_packet_current_canonical_v1_20260609.md`.
- Prior repo-side hook audit files except leaving their existing dirt untouched.
- GitHub, branches, worktrees, DB, Qdrant, news, memory, services, prompts, model/GPU config.
