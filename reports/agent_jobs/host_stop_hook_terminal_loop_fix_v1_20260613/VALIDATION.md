# Validation

## Commands Run

```text
pwd && git branch --show-current && git rev-parse HEAD && git remote -v && git status --short --untracked-files=all
Exit: 0
Result: branch safe/cockpit-news-context-date-filter-merge-packets-preserve-v1-20260609, HEAD 9dfa0f83cc09bf2e9edf40f659e0e2fdce0fa374, with pre-existing repo-hook audit dirt and count-24 packet.
```

```text
python3 scripts/agent_job_registry.py list-active --read-only --repo-root .
Exit: 0
Result: ok=true, active_jobs=[]
```

```text
python3 scripts/agent_job_contract.py validate docs/agent_tasks/host_stop_hook_terminal_loop_fix_v1_20260613.md
Exit: 0
Result: ok=true, issues=[]
```

```text
python3 -m py_compile /home/l4nd0/.codex/hooks/stop_check.py reports/agent_jobs/host_stop_hook_terminal_loop_fix_v1_20260613/stop_check_self_check.py
Exit: 0
```

```text
python3 reports/agent_jobs/host_stop_hook_terminal_loop_fix_v1_20260613/stop_check_self_check.py
Exit: 0
Result:
PASS: first terminal dirty warning emitted
PASS: repeated terminal dirty warning suppressed
PASS: non-terminal dirty warnings still emit
```

```text
CODEX_STOP_CHECK_REPO=/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1 CODEX_STOP_CHECK_TERMINAL_HANDOFF=1 CODEX_STOP_CHECK_CACHE_DIR=/tmp/codex-stop-check-live-smoke python3 /home/l4nd0/.codex/hooks/stop_check.py
Exit: 0
Result: first call emitted MILESTONE NOT COMMITTED warning with informational wording; second identical terminal call returned {}
```

```text
sha256sum /home/l4nd0/.codex/hooks/stop_check.py
Exit: 0
Result: 313b1040dde552fd441b4d77f89b1316221a64fbb7295ec284f0eb53acfe7738
```

```text
stat -c '%a %n' /home/l4nd0/.codex/hooks/stop_check.py
Exit: 0
Result: 755 /home/l4nd0/.codex/hooks/stop_check.py
```

## Final Guards

```text
python3 scripts/agent_job_contract.py validate docs/agent_tasks/host_stop_hook_terminal_loop_fix_v1_20260613.md && python3 -m py_compile /home/l4nd0/.codex/hooks/stop_check.py reports/agent_jobs/host_stop_hook_terminal_loop_fix_v1_20260613/stop_check_self_check.py && python3 reports/agent_jobs/host_stop_hook_terminal_loop_fix_v1_20260613/stop_check_self_check.py
Exit: 0
```

```text
python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/host_stop_hook_terminal_loop_fix_v1_20260613.md --repo-root . --no-write-report
Exit: 1
Result: failed only on pre-existing unrelated dirty files outside this task-card allowlist:
- scripts/agent_job_hook.py
- scripts/test_agent_job_hook.py
- docs/agent_tasks/goal_monitor_stop_loop_audit_v1_20260613.md
- docs/agent_tasks/extraction_count24_approval_packet_current_canonical_v1_20260609.md
```

```text
Changed-path guard excluding pre-existing unrelated dirt
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
?? docs/agent_tasks/host_stop_hook_terminal_loop_fix_v1_20260613.md
```

## Expected Check-Diff Caveat

Task-card `check-diff` is expected to report unrelated existing dirty files outside this task card:

- `scripts/agent_job_hook.py`
- `scripts/test_agent_job_hook.py`
- `docs/agent_tasks/goal_monitor_stop_loop_audit_v1_20260613.md`
- `docs/agent_tasks/extraction_count24_approval_packet_current_canonical_v1_20260609.md`

Those were intentionally not touched by this host-hook task.

## Final Status

`DONE_WITH_RISK`: host-global hook fix is implemented and focused validation passed. Residual risk is limited to expected existing repo dirt that blocks literal task-card `check-diff`.

## PR Preservation

The clean PR worktree preserved host-global hook evidence without tracking the
host hook file itself. See `HOST_GLOBAL_STOP_HOOK_EVIDENCE.md`.

## Clean PR Worktree Validation

Clean worktree:

```text
/home/l4nd0/tenn-goal-monitor-stop-loop-fix-v1-20260613
```

Base:

```text
origin/migration/clean-runtime-baseline-reconstruct-v1
HEAD efd11b9a44d9d73bf94b86f6d90c8f75342bb0cf
```

Commands:

```text
python3 scripts/agent_job_contract.py validate docs/agent_tasks/goal_monitor_stop_loop_audit_v1_20260613.md
Exit: 0
```

```text
python3 scripts/agent_job_contract.py validate docs/agent_tasks/host_stop_hook_terminal_loop_fix_v1_20260613.md
Exit: 0
```

```text
python3 -m py_compile scripts/agent_job_hook.py scripts/test_agent_job_hook.py
Exit: 0
```

```text
Synthetic repo hook self-check
Exit: 0
Result:
PASS: Codex Stop success returns {}
PASS: Codex BeforeTool pass context still emits
```

```text
python3 reports/agent_jobs/host_stop_hook_terminal_loop_fix_v1_20260613/stop_check_self_check.py
Exit: 0
Result:
PASS: first terminal dirty warning emitted
PASS: repeated terminal dirty warning suppressed
PASS: non-terminal dirty warnings still emit
```

```text
python3 -m pytest -q scripts/test_agent_job_hook.py
Exit: 1
Result: /usr/bin/python3: No module named pytest
```

No dependencies were installed.
