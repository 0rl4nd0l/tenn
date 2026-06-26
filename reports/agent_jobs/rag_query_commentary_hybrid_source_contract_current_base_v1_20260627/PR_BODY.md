## Summary

- Narrow `/rag/query` `source` validation to implemented backend sources: `asx_docs` and `news`.
- Remove the `commentary` and `hybrid` 501 stubs so those unsupported values are rejected by request validation.
- Add route-contract tests for accepted and rejected source values.
- Update the backend API surface doc to match the route contract.

Closes #252.

## Validation

- `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_rag_query_route_contract.py -q`
  - red before implementation: `commentary`/`hybrid` returned 501 instead of 422
  - green after implementation: 4 passed, 5 warnings
- `uv run --with ruff ruff check financial-engine_v2/backend/app/main.py financial-engine_v2/backend/tests/test_rag_query_route_contract.py`
- `python3 -m py_compile financial-engine_v2/backend/app/main.py financial-engine_v2/backend/tests/test_rag_query_route_contract.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/rag_query_commentary_hybrid_source_contract_current_base_v1_20260627.md`

## Runtime Proof

Runtime functionality proof is `PARTIAL`: focused route-contract tests pass, but
no live backend runtime was started.
