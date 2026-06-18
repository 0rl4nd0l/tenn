# Validation

## Commands

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/dev_flow_ledger_runtime_handoff_replay_v1_20260618.md`
  - exit: 0
  - result: `ok: true`
- `python3 scripts/agent_task_ledger.py resolve-path`
  - exit: 0
  - result:
    `/mnt/sdb2/home/l4nd0/tenn/.git/tenn-agent-registry/task-ledger.jsonl`
- `python3 scripts/agent_task_ledger.py validate`
  - exit: 0
  - result: `ok: true`
  - note: live ledger source reported `DATA_MISSING`; committed ledger source
    was present.
- `python3 -m pytest tests/test_agent_task_ledger.py -q`
  - exit: 1
  - result: `/usr/bin/python3: No module named pytest`
- `uv run --no-project --no-cache --with pytest pytest tests/test_agent_task_ledger.py -q`
  - first exit: 1
  - result: the handoff template heading contract failed because replay merge
    resolution used incompatible heading casing/spacing.
- `uv run --no-project --no-cache --with pytest pytest tests/test_agent_task_ledger.py -q`
  - second exit: 1
  - result: additional exact-case heading mismatches remained.
- `uv run --no-project --no-cache --with pytest pytest tests/test_agent_task_ledger.py -q`
  - third exit: 1
  - result: one remaining exact-case heading mismatch remained.
- `uv run --no-project --no-cache --with pytest pytest tests/test_agent_task_ledger.py -q`
  - final exit: 0
  - result: `14 passed, 1 warning, 6 subtests passed`
- `python3 scripts/agent_job_contract.py check-artifacts docs/agent_tasks/dev_flow_ledger_runtime_handoff_replay_v1_20260618.md`
  - exit: 0
  - result: `ok: true`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/dev_flow_ledger_runtime_handoff_replay_v1_20260618.md --no-write-report`
  - exit: 0
  - result: `ok: true`; `disallowed_files: []`
- `git diff --cached --check`
  - exit: 0
  - result: no whitespace errors
- `git diff --cached --name-only -- financial-engine_v2 count-24 scripts/count-24 docs/count-24 data .codex`
  - exit: 0
  - result: no product/runtime/data/count-24/Codex config paths in staged diff
- `tenn-code-reviewer` final diff gate
  - decision: `pass`
  - result: no findings for disallowed path changes, owner approval gaps,
    product/runtime/data/extraction boundary crossing, stale canonical rollback,
    or missing focused validation.

## Notes

- Validation is focused on task-card contract, ledger helper behavior, focused
  task-ledger tests, diff allowlist, and whitespace checks.
- No runtime services, database writes, extraction jobs, backfills, or product
  code checks are required for this control-plane replay.
- `uv` was run with `--no-project --no-cache` so validation did not modify repo
  dependency files or persistent dependency caches.
