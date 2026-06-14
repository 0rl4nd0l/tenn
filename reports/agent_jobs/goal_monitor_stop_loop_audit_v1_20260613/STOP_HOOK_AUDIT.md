# Stop Hook Audit

## Repo Stop Hook

`.codex/hooks.json` configures:

```text
python3 scripts/agent_job_hook.py --platform codex --event Stop
```

`scripts/agent_job_hook.py` does this:

- Finds an active task card from `TENN_AGENT_TASK_CARD` or `.tenn/active_agent_task`.
- Validates the task card.
- Runs registry `list-active`, `check-overlap`, and task-card `check-diff`.
- Returns `decision: block` when those checks fail.
- Previously returned a success `systemMessage` when those checks passed.

Before this patch, a successful Codex Stop check still injected new context:

```json
{"systemMessage": "Tenn agent-job contract passed: <task-card>"}
```

That is not useful after a terminal handoff/report and can contribute to repeated post-stop output.

## Host Stop Hook

Global `~/.codex/hooks.json` also configures:

```text
python3 /home/l4nd0/.codex/hooks/stop_check.py
```

That script:

- Hard-codes `REPO = "/home/l4nd0/tenn"`.
- Reads changed, staged, and untracked files.
- Emits `MILESTONE NOT COMMITTED` for any changed files.
- Emits a diff summary and optional docs warning.

Live synthetic run exited 0 and emitted:

```text
MILESTONE NOT COMMITTED: 2 file(s) changed and not committed (...count24..., ...goal_monitor...)
```

This is informational guidance, but it is emitted as a Stop-hook `systemMessage`, so it can cause the model to continue responding after it was otherwise done.

## Enforcement

Repo Stop hook can enforce task-card contract failures by returning `decision: block`.

Host `stop_check.py` does not enforce a terminal state. It only warns. It also does not know whether a handoff has completed or whether the warning has already been shown.

## Dirty Warning Loop Risk

Yes. A dirty milestone warning can cause repeated loop output because:

- It repeats on every Stop while the dirty state remains.
- It does not distinguish pre-existing unrelated dirt from current task dirt.
- It does not distinguish informational preservation advice from a requirement for more work.
- It does not suppress itself after a completed handoff.
