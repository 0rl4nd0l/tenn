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
- `python3 -m unittest tests/test_agent_task_ledger.py`
  - exit: 0
  - result: `Ran 17 tests`; `OK`
- `python3 scripts/agent_task_ledger.py append --help`
  - exit: 0
  - result: confirms `append` accepts `--entry-json` or `--entry-file`, plus
    optional `--ledger-path` and `--fill-identity`
- `uv run --no-project --no-cache --with pytest pytest tests/test_agent_task_ledger.py -q`
  - exit: 0
  - result: `17 passed, 1 warning, 6 subtests passed`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/dev_flow_ledger_runtime_handoff_replay_v1_20260618.md --no-write-report`
  - exit: 0
  - result: `ok: true`; `disallowed_files: []`
- `git diff --check`
  - exit: 0
  - result: no whitespace errors
- `git diff --name-only -- financial-engine_v2 count-24 scripts/count-24 docs/count-24 data .codex`
  - exit: 0
  - result: no product/runtime/data/count-24/Codex config paths in fix diff
- `tenn-code-reviewer` P2-fix diff gate
  - decision: `pass`
  - result: no findings for disallowed paths, weak validation, owner approval
    gaps, product/runtime/data/extraction boundary crossing, or stale canonical
    rollback.
- `python3 -m unittest tests/test_agent_task_ledger.py`
  - exit: 0
  - result: `Ran 18 tests`; `OK`
- `uv run --no-project --no-cache --with pytest pytest tests/test_agent_task_ledger.py -q`
  - exit: 0
  - result: `18 passed, 1 warning, 6 subtests passed`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/dev_flow_ledger_runtime_handoff_replay_v1_20260618.md --no-write-report`
  - exit: 0
  - result: `ok: true`; `disallowed_files: []`
- `git diff --check`
  - exit: 0
  - result: no whitespace errors
- Codex Review third P2 follow-up
  - decision: addressed
  - result: duplicate-work classification now remains
    `DATA_MISSING_FALLBACK_REQUIRED` whenever a ledger source is missing, even
    if stale committed-ledger matches exist.
- `python3 -m unittest tests/test_agent_task_ledger.py`
  - exit: 0
  - result: `Ran 19 tests`; `OK`
- `uv run --no-project --no-cache --with pytest pytest tests/test_agent_task_ledger.py -q`
  - exit: 0
  - result: `19 passed, 1 warning, 6 subtests passed`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/dev_flow_ledger_runtime_handoff_replay_v1_20260618.md --no-write-report`
  - exit: 0
  - result: `ok: true`; `disallowed_files: []`
- `git diff --check`
  - exit: 0
  - result: no whitespace errors
- Codex Review append-write P2 follow-up
  - decision: addressed
  - result: `append_entry()` now converts ledger create/open/write `OSError`
    failures into structured JSON errors through `LedgerError`.
- `python3 -m unittest tests/test_agent_task_ledger.py`
  - exit: 0
  - result: `Ran 20 tests`; `OK`
- `uv run --no-project --no-cache --with pytest pytest tests/test_agent_task_ledger.py -q`
  - exit: 0
  - result: `20 passed, 1 warning, 6 subtests passed`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/dev_flow_ledger_runtime_handoff_replay_v1_20260618.md --no-write-report`
  - exit: 0
  - result: `ok: true`; `disallowed_files: []`
- `git diff --check`
  - exit: 0
  - result: no whitespace errors
- Codex Review latest-ledger-state P2 follow-up
  - decision: addressed
  - result: duplicate-work classification now collapses append-only history to
    the latest entry per task before applying status priority.
- `python3 -m unittest tests/test_agent_task_ledger.py`
  - exit: 0
  - result: `Ran 21 tests`; `OK`
- `uv run --no-project --no-cache --with pytest pytest tests/test_agent_task_ledger.py -q`
  - exit: 0
  - result: `21 passed, 1 warning, 6 subtests passed`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/dev_flow_ledger_runtime_handoff_replay_v1_20260618.md --no-write-report`
  - exit: 0
  - result: `ok: true`; `disallowed_files: []`
- `git diff --check`
  - exit: 0
  - result: no whitespace errors
- Codex Review atomic-snapshot P2 follow-up
  - decision: addressed
  - result: `export-summary --write` now preflights both committed snapshot
    targets, writes both temp files first, and reports structured JSON errors
    before changing either target when a target is invalid.
- `python3 -m unittest tests/test_agent_task_ledger.py`
  - exit: 0
  - result: `Ran 22 tests`; `OK`
- `uv run --no-project --no-cache --with pytest pytest tests/test_agent_task_ledger.py -q`
  - exit: 0
  - result: `22 passed, 1 warning, 6 subtests passed`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/dev_flow_ledger_runtime_handoff_replay_v1_20260618.md --no-write-report`
  - exit: 0
  - result: `ok: true`; `disallowed_files: []`
- `git diff --check`
  - exit: 0
  - result: no whitespace errors
- Codex Review summary-latest-state P2 follow-up
  - decision: addressed
  - result: ledger summaries now group only the latest entry per task, matching
    duplicate-work classification behavior.
- `python3 -m unittest tests/test_agent_task_ledger.py`
  - exit: 0
  - result: `Ran 23 tests`; `OK`
- `uv run --no-project --no-cache --with pytest pytest tests/test_agent_task_ledger.py -q`
  - exit: 0
  - result: `23 passed, 1 warning, 6 subtests passed`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/dev_flow_ledger_runtime_handoff_replay_v1_20260618.md --no-write-report`
  - exit: 0
  - result: `ok: true`; `disallowed_files: []`
- `git diff --check`
  - exit: 0
  - result: no whitespace errors
- Codex Review missing-timestamp sort P2 follow-up
  - decision: addressed
  - result: `DATA_MISSING` timestamps now sort before real ISO timestamps when
    selecting the latest ledger entry per task.
- `python3 -m unittest tests/test_agent_task_ledger.py`
  - exit: 0
  - result: `Ran 24 tests`; `OK`
- `uv run --no-project --no-cache --with pytest pytest tests/test_agent_task_ledger.py -q`
  - exit: 0
  - result: `24 passed, 1 warning, 6 subtests passed`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/dev_flow_ledger_runtime_handoff_replay_v1_20260618.md --no-write-report`
  - exit: 0
  - result: `ok: true`; `disallowed_files: []`
- `git diff --check`
  - exit: 0
  - result: no whitespace errors
- Codex Review full-append-write P2 follow-up
  - decision: addressed
  - result: `append_entry()` now loops until the full JSONL payload is written
    and errors on zero-byte writes.

## Notes

- Validation is focused on task-card contract, ledger helper behavior, focused
  task-ledger tests, diff allowlist, and whitespace checks.
- No runtime services, database writes, extraction jobs, backfills, or product
  code checks are required for this control-plane replay.
- `uv` was run with `--no-project --no-cache` so validation did not modify repo
  dependency files or persistent dependency caches.
