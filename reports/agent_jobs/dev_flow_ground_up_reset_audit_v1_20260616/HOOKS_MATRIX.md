# Hooks Matrix

| Hook Surface | Current Behavior | Useful? | Risk | Classification | Recommendation |
| --- | --- | --- | --- | --- | --- |
| Repo `.codex/hooks.json` PreToolUse | Emits Graphify reminder for shell commands when graph exists. | Sometimes. | Low, can distract. | `CORE_KEEP` | Keep but make quiet. |
| Repo `.codex/hooks.json` Stop | Runs `python3 scripts/agent_job_hook.py --platform codex --event Stop`. | Yes. | Path drift can block or warn incorrectly. | `CORE_KEEP` | Keep; Git guard should preflight hook health. |
| Repo `.githooks/pre-commit` | Runs Ruff on staged Python if venv Ruff exists. | Yes. | Skips silently if Ruff missing. | `CORE_KEEP` | Keep. |
| Repo `.githooks/pre-push` | Runs Ruff, hook/tooling pytest, markdown hygiene. | Yes. | Current file is dirty in this checkout; owner-bound. | `CORE_KEEP` | Preserve, review separately before cleanup. |
| Claude hooks | Session memory, edit warnings, auto Ruff/chmod/test, Stop reminders. | Mixed. | Tool-specific and can be noisy. | `RENAME_OR_REHOME` | Keep as Claude surface, not Tenn universal policy. |
| Host `goal_optimizer_pre_tool.py` | Warns on high-burn commands in active goals. | Yes. | Warning-only. | `CORE_KEEP` | Keep. |
| Host `pre_apply_patch.py` | Warns on sensitive paths. | Yes. | Warning-only. | `CORE_KEEP` | Keep. |
| Host `post_apply_patch.py` | Runs Ruff/chmod/backend tests after patches. | Mixed. | Can create side effects in report-only runs. | `UNKNOWN_NEEDS_OWNER_DECISION` | Decide whether Tenn report-only paths should be exempt. |
| Host `stop_check.py` | Warns about uncommitted state. | Yes. | Defaults to `/home/l4nd0/tenn` if repo detection fails. | `MERGE_INTO_NEW_WORKFLOW` | Align with Tenn `tenn-git-guard`. |

## Hook Integration Target

Hooks should not be the primary workflow brain. They should enforce or warn on:

- active task card exists when mutation starts;
- diff stays inside allowed files;
- registry read-only/list-active is possible;
- dirty state and report artifacts are visible at Stop;
- no broad output or high-burn exploration continues unchecked.

The operator-facing commands should run the same checks before work starts so
Stop hooks are a backstop, not the first time a problem is discovered.
