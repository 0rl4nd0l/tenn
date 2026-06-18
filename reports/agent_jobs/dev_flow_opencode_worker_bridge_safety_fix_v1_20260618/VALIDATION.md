# Validation

## Completed

| Check | Result |
| --- | --- |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/dev_flow_opencode_worker_bridge_safety_fix_v1_20260618.md` | PASS |
| `python3 -m py_compile scripts/opencode_worker_bridge.py tests/test_opencode_worker_bridge.py` | PASS |
| `python3 -m unittest tests.test_opencode_worker_bridge` | PASS, 20 tests |
| Parse `.agents/skills/codex-worker-bridge/SKILL.md` frontmatter | PASS |
| `git diff --check` | PASS |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/dev_flow_opencode_worker_bridge_safety_fix_v1_20260618.md --no-write-report` | PASS |
| `git diff --check && git diff --cached --check` | PASS |
| Changed-path guard | PASS |
| Product/runtime/data/extraction/count-24 guard | PASS |
| Dependency/lockfile guard | PASS |
| Host-global guard | PASS |
