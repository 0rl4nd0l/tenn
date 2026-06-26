# Validation

## Preflight

- `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /home/l4nd0/tenn-issue227-cockpit-marketplace-state-route-guard-current-base-v1-20260627 --topic issue227-cockpit-marketplace-state-route-guard --json`
  - Exit: 0
  - Result: `final_decision=pass`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_marketplace_state_route_guard_v1_20260602.md`
  - Exit: 0
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_marketplace_state_route_guard_v1_20260602.md --repo-root .`
  - Exit: 0
- `python3 scripts/agent_task_ledger.py --repo-root . search --text cockpit_marketplace_state_route_guard_v1_20260602`
  - Exit: 0
  - Result: active claim found for this worktree/task.

## RED

Temp red worktree:
`/tmp/tenn-issue227-red-current-base-20260627`

Setup:

- Detached at `origin/migration/clean-runtime-baseline-reconstruct-v1`
  (`7d6ab6c184332d5413700eb08e6790f530000942`).
- Applied only the final backend test diff.
- Removed after the red run.

Command:

```bash
PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_cockpit_marketplace_api.py financial-engine_v2/backend/tests/test_local_api_key.py -q
```

Exit: 1

Expected result:

- `43 failed, 35 passed, 5 warnings`
- Failures showed missing 401 responses on configured Marketplace state routes
  and missing route-level API-key dependency registration.

## GREEN

Command:

```bash
PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_cockpit_marketplace_api.py financial-engine_v2/backend/tests/test_local_api_key.py -q
```

Exit: 0

Result:

- `78 passed, 5 warnings`

## Static Checks

- `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt ruff check financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_cockpit_marketplace_api.py financial-engine_v2/backend/tests/test_local_api_key.py`
  - Exit: 0
  - Result: `All checks passed!`
- `python3 -m py_compile financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_cockpit_marketplace_api.py financial-engine_v2/backend/tests/test_local_api_key.py`
  - Exit: 0
- `git diff --check`
  - Exit: 0
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_marketplace_state_route_guard_v1_20260602.md`
  - Exit: 0
- `python3 scripts/agent_task_ledger.py --repo-root . validate`
  - Exit: 0
  - Result: no issues, no `DATA_MISSING`

## Frontend Evidence

No frontend source changed in this lane.

Current evidence:

- `cockpit-ui/lib/marketplace-api.ts` uses `buildHeaders(apiKey, ...)` for
  Marketplace mission, match, feedback, benchmark-review, link/unlink, and alert
  client calls.
- `cockpit-ui/lib/marketplace-routes.test.ts` contains BFF header forwarding
  assertions for mission, match, tracked-product, eBay sync, and mission
  link/unlink routes.

Frontend test command was not run because no frontend file changed.

## Closeout

- Draft PR: #446, `https://github.com/0rl4nd0l/tenn/pull/446`
- PR body issue reference: `Closes #227`
- Registry release command:

```bash
python3 scripts/agent_job_registry.py release cockpit_marketplace_state_route_guard_v1_20260602 --repo-root .
```

- Exit: 0
