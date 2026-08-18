## Summary

- add deterministic `source_kind` to recent commentary endpoint items
- preserve Recent sources `sourceKind` through the Cockpit drawer reattach callback
- reattach Recent sources in chat using the provided kind instead of hardcoding `ephemeral`

Closes #213.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_recent_sources_source_kind_current_base_v1_20260627.md`
- `python3 scripts/agent_job_registry.py check-overlap --repo-root . docs/agent_tasks/cockpit_recent_sources_source_kind_current_base_v1_20260627.md`
- `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_commentary_recent_endpoint.py -q`
- `uv run --with ruff ruff check financial-engine_v2/backend/app/api/commentary.py financial-engine_v2/backend/tests/test_commentary_recent_endpoint.py`
- `python3 -m py_compile financial-engine_v2/backend/app/api/commentary.py financial-engine_v2/backend/tests/test_commentary_recent_endpoint.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_recent_sources_source_kind_current_base_v1_20260627.md`

## Local Validation Gap

- `npm test -- components/cockpit/chat/sources-drawer.test.tsx` blocked locally because `vitest` is not installed in `cockpit-ui/node_modules/.bin`.
- `npm run lint -- components/cockpit/chat/sources-drawer.tsx components/cockpit/chat/chat-screen.tsx` blocked locally because `eslint` is not installed in `cockpit-ui/node_modules/.bin`.
- No dependency install was performed.

## Safety

- No DB, Qdrant, Redis, news store, memory store, source PDF, extraction output, gold-label, runtime/model/GPU/service config, or production data mutation.
