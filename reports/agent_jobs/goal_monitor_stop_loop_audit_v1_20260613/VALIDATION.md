# Validation

## Commands Run

```text
pwd && git branch --show-current && git rev-parse HEAD && git remote -v && git status --short --untracked-files=all
Exit: 0
```

```text
python3 scripts/agent_job_registry.py list-active --read-only --repo-root .
Exit: 0
Result: ok=true, active_jobs=[]
```

```text
python3 scripts/agent_job_contract.py validate docs/agent_tasks/goal_monitor_stop_loop_audit_v1_20260613.md
Exit: 0
Result: ok=true, issues=[]
```

```text
python3 -m pytest -q scripts/test_agent_job_hook.py
Exit: 1
Result: /usr/bin/python3: No module named pytest
```

```text
uv run pytest -q scripts/test_agent_job_hook.py
Exit: 2
Result: Failed to spawn pytest; No such file or directory
```

```text
python3 -m py_compile scripts/agent_job_hook.py scripts/test_agent_job_hook.py
Exit: 0
```

```text
Synthetic hook self-check in temp git repo
Exit: 0
Result:
Stop 0 {}
BeforeTool 0 {"systemMessage": "Tenn agent-job contract passed: docs/agent_tasks/test-task.md"}
```

```text
git diff --check
Exit: 0
```

## Final Guards

```text
python3 scripts/agent_job_contract.py validate docs/agent_tasks/goal_monitor_stop_loop_audit_v1_20260613.md
Exit: 0
Result: ok=true, issues=[]
```

```text
python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/goal_monitor_stop_loop_audit_v1_20260613.md --repo-root . --no-write-report
Exit: 1
Result: failed only because pre-existing docs/agent_tasks/extraction_count24_approval_packet_current_canonical_v1_20260609.md is outside allowed_files.
```

```text
Changed-path guard excluding the pre-existing count-24 packet
Exit: 0
Result: violations=[]
```

```text
git diff --check && git status --short --untracked-files=all
Exit: 0
Status:
 M scripts/agent_job_hook.py
 M scripts/test_agent_job_hook.py
?? docs/agent_tasks/extraction_count24_approval_packet_current_canonical_v1_20260609.md
?? docs/agent_tasks/goal_monitor_stop_loop_audit_v1_20260613.md
```

## Validation Gap

Focused pytest could not run because `pytest` is unavailable in the current Python and `uv run` environments. Syntax checks and synthetic hook self-checks passed.

## Final Status

`DONE_WITH_RISK`: the scoped repo fix is implemented and focused self-checks pass; residual risk remains in the host-global Stop hook and pytest is unavailable.

## Clean PR Worktree Preservation

The repo-side hook fix was reconstructed into clean sibling worktree:

```text
/home/l4nd0/tenn-goal-monitor-stop-loop-fix-v1-20260613
```

The clean worktree validation reconfirmed:

- `python3 -m py_compile scripts/agent_job_hook.py scripts/test_agent_job_hook.py` exited 0.
- Synthetic Codex `Stop` success returned `{}`.
- Synthetic Codex `BeforeTool` pass context still emitted.
- `pytest` remains unavailable: `/usr/bin/python3: No module named pytest`.
