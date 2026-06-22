# Validation

Status: passed.

## Commands
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/control_plane_runtime_functionality_proof_closeout_gate_v1_20260622.md`: passed
- `python3 scripts/agent_task_ledger.py resolve-path && python3 scripts/agent_task_ledger.py validate`: passed with live ledger `DATA_MISSING` and committed ledger present
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`: passed, `active_jobs: []`, `read_only: true`, `lock_acquired: false`
- `python3 scripts/check_runtime_functionality_proof_docs.py`: passed, 9 fields checked
- `python3 -m py_compile scripts/agent_job_contract.py scripts/agent_job_hook.py`: passed
- `python3 -m pytest scripts/test_agent_job_contract.py scripts/test_agent_job_hook.py`: failed because system Python has no `pytest`
- `uv run --with pytest --with pyyaml python -m pytest scripts/test_agent_job_contract.py scripts/test_agent_job_hook.py`: passed, 53 tests
- `git diff --check`: passed
- `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/control_plane_runtime_functionality_proof_closeout_gate_v1_20260622.md --repo-root .`: passed
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/control_plane_runtime_functionality_proof_closeout_gate_v1_20260622.md --repo-root .`: passed
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/control_plane_runtime_functionality_proof_closeout_gate_v1_20260622.md --repo-root .`: passed

## Boundary Guards
- Product/runtime/data/extraction/count-24 path guard: passed for current tracked diff.
- Host-global path guard: passed; all changed files are repo-local paths.

## Runtime Functionality Proof
- Required: no
- Reason: This PR changes control-plane validation and hook tooling only.
