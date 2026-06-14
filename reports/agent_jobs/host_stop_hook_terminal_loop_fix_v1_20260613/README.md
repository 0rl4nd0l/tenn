# Host Stop Hook Terminal Loop Fix V1

Status: DONE_WITH_RISK

## Objective

Fix the host-global Codex Stop hook loop after terminal handoff while leaving Tenn product/runtime/data/extraction work untouched.

## What Changed

Patched `/home/l4nd0/.codex/hooks/stop_check.py`.

The hook still emits useful dirty milestone warnings, but now it suppresses repeated identical warnings when terminal/handoff-complete state is detected. It returns `{}` on the repeated terminal warning instead of adding another `systemMessage` for Codex to answer.

## Dirty State Detection

The hook detects dirty milestone state with:

- `git diff --name-only HEAD`
- `git diff --cached --name-only`
- `git ls-files --others --exclude-standard`
- `git diff --stat HEAD`

## Terminal / Handoff Detection

Terminal state is detected from explicit hook/env markers, existing handoff path markers, payload goal status, or `CODEX_THREAD_ID` status in `~/.codex/goals_1.sqlite`.

## Loop Guard

When terminal/handoff state is true, the hook fingerprints the repo and warning text under `/tmp/codex-stop-check/`. The first warning can still appear; the second identical warning for the same thread/repo is suppressed.

## Validation

Focused self-check passed:

- first terminal dirty warning emitted
- repeated terminal dirty warning suppressed
- non-terminal dirty warnings still emit

Final guards passed for syntax, self-check, `git diff --check`, and changed-path scope. Task-card `check-diff` failed only on pre-existing unrelated repo dirt from the prior hook audit and count-24 packet.

## Files Touched

- `/home/l4nd0/.codex/hooks/stop_check.py`
- `docs/agent_tasks/host_stop_hook_terminal_loop_fix_v1_20260613.md`
- `reports/agent_jobs/host_stop_hook_terminal_loop_fix_v1_20260613/*`

## PR Preservation Note

The host-global hook file itself is not tracked in this repo PR. The PR preserves
host-local evidence in `HOST_GLOBAL_STOP_HOOK_EVIDENCE.md` and preserves the
focused self-check script in this report bundle.

## Files Intentionally Not Touched

- Tenn product/runtime/data/extraction files
- count-24 packet
- GitHub
- branches/worktrees
- prior repo-side hook audit files, except they remain as existing dirt

## Remaining Risk

This stops repeated identical terminal dirty-warning loops. It does not suppress first-use warnings, and it intentionally does not suppress repeated non-terminal warnings.

## Next Recommended Prompt

Review `/home/l4nd0/.codex/hooks/stop_check.py` behavior after the next terminal `/goal` closeout. If it still emits unwanted first-use terminal warnings, decide whether terminal state should suppress the first warning too.
