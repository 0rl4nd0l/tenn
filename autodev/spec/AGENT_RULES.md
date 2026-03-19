# AGENT RULES

## Mandatory behavior
- Only work on `agent/YYYY-MM-DD/<task_slug>` branches.
- Refuse direct commits or pushes to `main` and `master`.
- Keep changes incremental and task-scoped.
- Run gates in order: `ruff` -> `pytest` -> `eval`.
- Persist all command logs for every run.
- Stop retrying a task after 10 attempts and emit failure escalation report.
- If task discovery is enabled, only append to `autodev/spec/TASKS.md`.

## Forbidden actions
- Running unallowlisted commands.
- Using networked commands by default (`curl`, `wget`, `ssh`, package installers).
- Deleting data recursively (`rm -rf`) or mutating protected branches.
- Claiming completion while any gate or threshold is failing.
- Enabling auto-merge unless explicitly configured by a human.
- Editing repository source files from task discovery logic.

## Escalation
- If retries exceed the configured max, mark task blocked.
- Produce a report with failure context, attempted fixes, and recommended next action.
