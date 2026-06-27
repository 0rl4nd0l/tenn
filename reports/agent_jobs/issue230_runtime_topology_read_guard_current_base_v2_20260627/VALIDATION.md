# Validation

## Passed

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue230_runtime_topology_read_guard_current_base_v2_20260627.md`
- `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_cockpit_api_models.py -q`
  - Result: `27 passed`
- `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt ruff check financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_cockpit_api_models.py`
  - Result: passed
- `python3 -m py_compile financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_cockpit_api_models.py`
  - Result: passed
- `uv run --with pytest python -m pytest scripts/test_cockpit_routing_smoke.py -q`
  - Result: `6 passed`, 1 pytest config warning
- `uv run --with ruff ruff check scripts/cockpit_routing_smoke.py scripts/test_cockpit_routing_smoke.py`
  - Result: passed
- `python3 -m py_compile scripts/cockpit_routing_smoke.py scripts/test_cockpit_routing_smoke.py`
  - Result: passed
- `python3 -m json.tool reports/agent_jobs/issue230_runtime_topology_read_guard_current_base_v2_20260627/status.json`
  - Result: passed
- `git diff --check`
  - Result: passed
- `git diff --cached --check`
  - Result: passed
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/issue230_runtime_topology_read_guard_current_base_v2_20260627.md --repo-root .`
  - Result: passed
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/issue230_runtime_topology_read_guard_current_base_v2_20260627.md --repo-root .`
  - Result: passed
- `python3 scripts/agent_task_ledger.py --repo-root . validate`
  - Result: passed

## Blocked Locally

- `npm test -- --run lib/api-client.test.ts`
  - Result: blocked, `vitest: not found`
- `npm run lint -- lib/api-client.ts lib/api-client.test.ts components/cockpit/cockpit-sidebar.tsx components/cockpit/cockpit-status-bar.tsx components/cockpit/settings/settings-screen.tsx components/cockpit/chat/chat-screen.tsx components/cockpit/verification/verification-screen.tsx components/cockpit/operations/gpu-workload-card.tsx`
  - Result: blocked, `eslint: not found`
- `python3 -m pytest scripts/test_cockpit_routing_smoke.py -q`
  - Result: blocked, system Python lacks pytest; rerun with `uv run --with pytest`

## Pending

- GitHub PR checks after push
- Fresh Codex review after PR open
