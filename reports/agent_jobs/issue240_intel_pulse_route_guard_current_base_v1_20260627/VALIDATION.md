# Validation

## Preflight

- `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /home/l4nd0/tenn-issue240-intel-pulse-route-guard-current-base-v1-20260627 --topic "issue240 intel pulse matrix route api key guard" --json`
  - PASS: clean current-base task worktree, canonical head
    `7d6ab6c184332d5413700eb08e6790f530000942`, no matching active work.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue240_intel_pulse_route_guard_current_base_v1_20260627.md`
  - PASS.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/issue240_intel_pulse_route_guard_current_base_v1_20260627.md --repo-root .`
  - PASS.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/issue240_intel_pulse_route_guard_current_base_v1_20260627.md --repo-root .`
  - PASS.
- `python3 scripts/agent_task_ledger.py --repo-root . validate`
  - PASS before source edits.
- `python3 scripts/agent_task_ledger.py --repo-root . append --fill-identity --entry-json ...`
  - PASS for `claimed` entry.

## RED

```bash
PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt pytest -q financial-engine_v2/backend/tests/test_local_api_key.py financial-engine_v2/backend/tests/test_cockpit_intel_pulse_route_auth.py
```

Result before source fix: FAIL as expected.

- 4 failed.
- 17 passed.
- 5 warnings.

## GREEN

```bash
PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt pytest -q financial-engine_v2/backend/tests/test_local_api_key.py financial-engine_v2/backend/tests/test_cockpit_intel_pulse_route_auth.py
```

Result after source fix: PASS.

- 21 passed.
- 5 warnings.

## Frontend

```bash
pnpm --dir cockpit-ui exec vitest run lib/api-client.test.ts
```

Result: BLOCKED.

- Exit code 254.
- `ERR_PNPM_RECURSIVE_EXEC_FIRST_FAIL Command "vitest" not found`.
- `cockpit-ui/node_modules` absent.
- `cockpit-ui/node_modules/.bin/vitest` absent.
- No dependency install was performed.

## Static Checks

```bash
uv run --with ruff ruff check financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_local_api_key.py financial-engine_v2/backend/tests/test_cockpit_intel_pulse_route_auth.py
```

Result: PASS, `All checks passed!`.

```bash
python3 -m py_compile financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_local_api_key.py financial-engine_v2/backend/tests/test_cockpit_intel_pulse_route_auth.py
```

Result: PASS.

```bash
git diff --check
```

Result: PASS.

## Not Run

- Live backend/Cockpit runtime smoke: not run; task forbids service starts and
  production data mutation.
- Frontend dependency install: not run; task forbids dependency or lockfile
  mutation.

## GitHub

- PR: <https://github.com/0rl4nd0l/tenn/pull/435>
- PR state at `2026-06-26T19:31:06Z`: OPEN, non-draft,
  `mergeStateStatus=UNSTABLE`.
- GitHub checks at `2026-06-26T19:31:06Z`: `scan` IN_PROGRESS,
  `lint-and-test` IN_PROGRESS.
