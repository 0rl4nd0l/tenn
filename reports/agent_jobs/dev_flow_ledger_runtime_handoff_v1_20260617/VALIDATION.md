# Validation

## Commands Run

| Command | Exit | Result |
| --- | ---: | --- |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/dev_flow_ledger_runtime_handoff_v1_20260617.md` | 0 | PASS |
| `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .` | 0 | PASS, no active jobs |
| `python3 -m py_compile scripts/agent_task_ledger.py` | 0 | PASS |
| `uv run --with pytest python -m pytest tests/test_agent_task_ledger.py` | 0 | PASS, 14 tests; pytest 9.1.0 on Python 3.11.15 |
| `python3 -m unittest tests.test_agent_task_ledger` | 0 | PASS, 14 tests |
| `python3 -m json.tool docs/dev_flow/templates/TASK_LEDGER_ENTRY.json` | 0 | PASS |
| `python3 scripts/agent_task_ledger.py --repo-root . validate --entry-file docs/agent_registry/task_ledger/LEDGER.jsonl` | 0 | PASS |
| `python3 scripts/agent_task_ledger.py --repo-root . validate --entry-file reports/agent_jobs/dev_flow_ledger_runtime_handoff_v1_20260617/handoff/LEDGER_ENTRY.json` | 0 | PASS |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/dev_flow_ledger_runtime_handoff_v1_20260617.md --repo-root . --no-write-report` | 0 | PASS |
| `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/dev_flow_ledger_runtime_handoff_v1_20260617.md --repo-root .` | 0 | PASS |
| `git diff --check` | 0 | PASS |
| changed `SKILL.md` frontmatter parse | 0 | PASS |
| missing custom ledger path regressions | 0 | PASS via unittest |
| changed-path guard | 0 | PASS |
| product/runtime/data/extraction/count-24/host-global guard | 1 | PASS, no matching changed paths |

## Environment Notes

- Existing repo pytest-capable venv: not found.
- `uv` path used: `/home/l4nd0/.local/bin/uv`.
- No `requirements.txt`, `pyproject.toml`, lockfiles, CI config, system package,
  production venv, or host-global config were modified.
