# Validation

## Passed

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_recent_sources_source_kind_current_base_v1_20260627.md`
- `python3 scripts/agent_job_registry.py check-overlap --repo-root . docs/agent_tasks/cockpit_recent_sources_source_kind_current_base_v1_20260627.md`
- `python3 scripts/agent_job_registry.py claim --repo-root . docs/agent_tasks/cockpit_recent_sources_source_kind_current_base_v1_20260627.md`
- `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_commentary_recent_endpoint.py -q`
  - Result: `4 passed, 5 warnings`
- `uv run --with ruff ruff check financial-engine_v2/backend/app/api/commentary.py financial-engine_v2/backend/tests/test_commentary_recent_endpoint.py`
  - Result: passed
- `python3 -m py_compile financial-engine_v2/backend/app/api/commentary.py financial-engine_v2/backend/tests/test_commentary_recent_endpoint.py`
  - Result: passed
- `git diff --check`
  - Result: passed
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_recent_sources_source_kind_current_base_v1_20260627.md`
  - Result: passed

## Red Evidence

- Backend focused test failed before implementation with `KeyError: 'source_kind'`, proving the missing endpoint field.

## Blocked Local UI Checks

- `npm test -- components/cockpit/chat/sources-drawer.test.tsx`
  - Result: blocked locally, `sh: 1: vitest: not found`
- `npm run lint -- components/cockpit/chat/sources-drawer.tsx components/cockpit/chat/chat-screen.tsx`
  - Result: blocked locally, `sh: 1: eslint: not found`

No dependency install was performed.
