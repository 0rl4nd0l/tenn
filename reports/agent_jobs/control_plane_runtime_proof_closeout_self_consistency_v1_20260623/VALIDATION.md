# Validation

Status: passed.

## Commands

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/control_plane_runtime_proof_closeout_self_consistency_v1_20260623.md`: exit 0.
- `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/control_plane_runtime_functionality_proof_closeout_gate_v1_20260622.md --repo-root .`: exit 0.
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/control_plane_runtime_functionality_proof_closeout_gate_v1_20260622.md --repo-root .`: exit 0.
- `python3 scripts/check_runtime_functionality_proof_docs.py`: exit 0,
  `runtime_functionality_proof_docs_ok`, fields=9.
- `uv run --with pytest --with pyyaml pytest scripts/test_agent_job_contract.py scripts/test_agent_job_hook.py`: exit 0, 58 passed, 1 warning.
- `git diff --check`: exit 0.
- `scripts/sync_codex_skills.sh`: exit 0, `would_link=10`.

## Boundary Guards

- Product/runtime/data/extraction/count-24 path guard: passed; tracked diff is
  limited to control-plane task-card/report files.
- Host-global path guard: passed; no host-global files changed.
- Visible repo-backed skill count before: 10 from `scripts/sync_codex_skills.sh`
  dry run.
- Visible repo-backed skill count after: 10 from `scripts/sync_codex_skills.sh`
  dry run.
