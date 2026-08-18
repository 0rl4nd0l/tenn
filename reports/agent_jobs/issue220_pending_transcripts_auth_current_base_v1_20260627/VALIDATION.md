# Validation

## Passed

```text
python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue220_pending_transcripts_auth_current_base_v1_20260627.md
```

Result: PASS.

```text
python3 scripts/agent_job_registry.py check-overlap --repo-root . docs/agent_tasks/issue220_pending_transcripts_auth_current_base_v1_20260627.md
python3 scripts/agent_job_registry.py claim --repo-root . docs/agent_tasks/issue220_pending_transcripts_auth_current_base_v1_20260627.md
```

Result: PASS; registry claim active for this task.

```text
uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_local_api_key.py -q
```

Result: 19 passed, 5 existing warnings.

```text
uv run --with pytest --with httpx pytest -q financial-engine_v2/backend/tests/test_backend_api_client_context.py::TestGetPendingTranscripts
```

Result: 2 passed, 1 existing warning.

```text
uv run --with ruff ruff check financial-engine_v2/backend/app/api/commentary.py financial-engine_v2/cockpit/integrations/backend_api.py financial-engine_v2/backend/tests/test_local_api_key.py financial-engine_v2/backend/tests/test_backend_api_client_context.py
```

Result: PASS.

```text
python3 -m py_compile financial-engine_v2/backend/app/api/commentary.py financial-engine_v2/cockpit/integrations/backend_api.py financial-engine_v2/backend/tests/test_local_api_key.py financial-engine_v2/backend/tests/test_backend_api_client_context.py
```

Result: PASS.

```text
git diff --check
```

Result: PASS.

## Known Validation Gaps

- Initial `pytest -k pending_transcripts` selected zero tests and exited 5; it
  was replaced by the exact node id command above.
- No live backend/Cockpit runtime was started.
- No live transcript staging store was queried.
