# Validation

## Completed

| Check | Result |
| --- | --- |
| `python3 scripts/agent_job_contract.py validate docs/agent_tasks/dev_flow_opencode_worker_bridge_v1_20260617.md` | PASS |
| `python3 -m py_compile scripts/opencode_worker_bridge.py tests/test_opencode_worker_bridge.py` | PASS |
| `python3 -m unittest tests.test_opencode_worker_bridge` | PASS, 16 tests |
| Parse changed `.agents/skills/codex-worker-bridge/SKILL.md` frontmatter | PASS |
| JSON-parse `docs/dev_flow/templates/OPENCODE_WORKER_META.json` | PASS |
| `git diff --check` | PASS |

## Probe

`python3 scripts/opencode_worker_bridge.py probe` completed successfully.

Summary:

- OpenCode available: `true`
- OpenCode command: `/home/l4nd0/.opencode/bin/opencode`
- OpenCode version: `1.3.17`
- DeepSeek available: `true`
- First listed agent: `build (primary)`
- DeepSeek models included:
  - `opencode/deepseek-v4-flash-free`
  - `deepseek/deepseek-chat`
  - `deepseek/deepseek-reasoner`
  - `deepseek/deepseek-v4-flash`
  - `deepseek/deepseek-v4-pro`

Readonly enforcement smoke:

- Method: `OPENCODE_CONFIG_CONTENT`
- Verification command: `opencode debug config`
- Global `edit`: `deny`
- Global `bash.*`: `deny`
- Global `external_directory`: `deny`
- Agent `edit`: `deny`
- Agent `bash.*`: `deny`
- Agent `external_directory`: `deny`

## Final Staged Checks

| Check | Result |
| --- | --- |
| `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/dev_flow_opencode_worker_bridge_v1_20260617.md --no-write-report` | PASS |
| Changed-path guard | PASS, 11 changed paths all in task-card allowlist |
| Product/runtime/data/extraction/count-24 guard | PASS |
| Dependency/lockfile guard | PASS |
| Host-global guard | PASS |
| `git diff --check && git diff --cached --check` | PASS |

## Ignored Artifacts

Python validation generated ignored cache directories:

- `scripts/__pycache__/`
- `tests/__pycache__/`

They are not staged.
