# Validation

## Red/Green

- RED:
  `uv run --with pytest --with pyyaml pytest scripts/test_agent_job_contract.py -q -k "board_decision"`
  - exit: 1
  - result: two new tests failed because non-runtime `check-closeout` returned
    early with no board artifacts.
- GREEN:
  `uv run --with pytest --with pyyaml pytest scripts/test_agent_job_contract.py -q -k "board_decision"`
  - exit: 0
  - result: 2 passed, 39 deselected, 1 existing pytest config warning.

## Passed Checks

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/control_plane_board_decision_closeout_gate_v1_20260623.md`
  - exit: 0
  - result: ok true.
- `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "BOARD_DECISION closeout gate wiring" --json`
  - exit: 0
  - result: final_decision pass; registry PASS; ledger PASS; duplicate work
    classification `NO_MATCHING_ACTIVE_WORK_FOUND`.
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
  - exit: 0
  - result: ok true; zero active jobs.
- `python3 scripts/agent_task_ledger.py validate`
  - exit: 0
  - result: ok true; 17 entries.
- `uv run --with pytest --with pyyaml pytest scripts/test_agent_job_contract.py scripts/test_check_board_decision.py scripts/test_agent_job_hook.py -q`
  - exit: 0
  - result: 70 passed, 1 existing pytest config warning.
- `python3 scripts/check_board_decision.py docs/dev_flow/templates/BOARD_DECISION.json --template`
  - exit: 0
  - result: ok true.
- `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/control_plane_board_decision_validator_v1_20260623.md --repo-root .`
  - exit: 0
  - result: ok true.
- `git diff --check`
  - exit: 0
  - result: no whitespace errors.
- `python3 -m py_compile scripts/agent_job_contract.py scripts/check_board_decision.py scripts/test_agent_job_contract.py`
  - exit: 0
  - result: no syntax errors.

## Final Report Checks

- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/control_plane_board_decision_closeout_gate_v1_20260623.md`
  - exit: 0
  - result: ok true; wrote
    `reports/agent_jobs/control_plane_board_decision_closeout_gate_v1_20260623/diff-check.json`.
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/control_plane_board_decision_closeout_gate_v1_20260623.md`
  - exit: 0
  - result: ok true; all six report artifacts exist and are non-empty.
- `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/control_plane_board_decision_closeout_gate_v1_20260623.md --repo-root .`
  - exit: 0
  - result: ok true.
