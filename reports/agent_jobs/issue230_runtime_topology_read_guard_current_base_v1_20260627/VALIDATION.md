# Validation

## Preflight

- `pwd && git branch --show-current && git rev-parse HEAD && git remote -v && git status --short --untracked-files=all`: exit 0; worktree is `/home/l4nd0/tenn-issue230-runtime-topology-read-guard-current-base-v1-20260627`, branch `safe/issue230-runtime-topology-read-guard-current-base-v1-20260627`, HEAD `7d6ab6c184332d5413700eb08e6790f530000942`, status clean.
- `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "issue230 cockpit runtime topology read guard" --json`: exit 0, `duplicate_work_classification=NO_MATCHING_ACTIVE_WORK_FOUND`.
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`: exit 0, active jobs empty before claim.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/issue230_runtime_topology_read_guard_current_base_v1_20260627.md --repo-root .`: exit 0.
- After direct UI config-fetch scope was added, registry record was refreshed:
  `release issue230_runtime_topology_read_guard_current_base_v1_20260627` exit
  0, then `claim ...` exit 0 with expanded allowlist.
- `python3 scripts/agent_task_ledger.py --repo-root . validate`: exit 0.
- `python3 scripts/agent_task_ledger.py --repo-root . append ...`: initial
  append exit 1 because this repo version required explicit identity fields;
  rerun with `owner`, `session_id`, `started_at`, and `updated_at` exit 0.

## RED

- Backend command:
  `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_cockpit_api_models.py -q`
- Exit: 1.
- Result: 9 failed, 18 passed.
- Expected failures: `/config`, `/models`, and `/queue` lacked
  `require_api_key`, and missing/wrong configured API keys reached runtime
  probing or returned queue status instead of 401.
- Frontend command:
  `npm test -- --run lib/api-client.test.ts`
- Exit: 127.
- Result: blocked locally, `vitest: not found`.

## GREEN

- Backend command:
  `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_cockpit_api_models.py -q`
- Exit: 0.
- Result: 27 passed.
- Frontend command after implementation:
  `npm test -- --run lib/api-client.test.ts`
- Exit: 127.
- Result: blocked locally, `vitest: not found`.

## Static Checks

- `uv run --with ruff ruff check financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_cockpit_api_models.py`: exit 0, all checks passed.
- `python3 -m py_compile financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_cockpit_api_models.py`: exit 0.
- `git diff --check`: exit 0.
- `npm run lint -- --file lib/api-client.ts --file lib/api-client.test.ts --file components/cockpit/cockpit-sidebar.tsx --file components/cockpit/cockpit-status-bar.tsx --file components/cockpit/settings/settings-screen.tsx --file components/cockpit/chat/chat-screen.tsx --file components/cockpit/verification/verification-screen.tsx --file components/cockpit/operations/gpu-workload-card.tsx`: exit 127, blocked locally, `eslint: not found`.

## Report Gates

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue230_runtime_topology_read_guard_current_base_v1_20260627.md`: exit 0.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/issue230_runtime_topology_read_guard_current_base_v1_20260627.md --repo-root .`: exit 0, no disallowed files.
- PR: https://github.com/0rl4nd0l/tenn/pull/440.
- Direct config fetch scan:
  `rg -n "fetch\\('/api/cockpit/config'" cockpit-ui/components/cockpit -g '*.tsx'`: all remaining direct config fetches are in the task-card allowlist and were updated with an API-key header path.
