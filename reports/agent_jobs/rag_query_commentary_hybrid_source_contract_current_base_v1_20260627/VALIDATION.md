# Validation

## Commands

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/rag_query_commentary_hybrid_source_contract_current_base_v1_20260627.md`
  - result: passed
- `python3 scripts/agent_job_registry.py check-overlap --repo-root . docs/agent_tasks/rag_query_commentary_hybrid_source_contract_current_base_v1_20260627.md`
  - result: passed; no active overlap
- `python3 scripts/agent_job_registry.py claim --repo-root . docs/agent_tasks/rag_query_commentary_hybrid_source_contract_current_base_v1_20260627.md`
  - result: passed
- `python3 scripts/agent_task_ledger.py --repo-root . validate`
  - result: passed before implementation; live ledger available
- `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_rag_query_route_contract.py -q`
  - red result before implementation: 2 failed, 2 passed, 5 warnings; `commentary` and `hybrid` returned 501 instead of expected 422
  - first setup attempt: errored because context-managed TestClient triggered startup Qdrant validation against `http://127.0.0.1:6333`
  - green result after implementation: 4 passed, 5 warnings
- `uv run --with ruff ruff check financial-engine_v2/backend/app/main.py financial-engine_v2/backend/tests/test_rag_query_route_contract.py`
  - result: passed
- `python3 -m py_compile financial-engine_v2/backend/app/main.py financial-engine_v2/backend/tests/test_rag_query_route_contract.py`
  - result: passed
- `git diff --check`
  - result: passed
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/rag_query_commentary_hybrid_source_contract_current_base_v1_20260627.md`
  - result: passed; no disallowed files
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/rag_query_commentary_hybrid_source_contract_current_base_v1_20260627.md`
  - result: passed
- `python3 scripts/agent_task_ledger.py --repo-root . validate`
  - result: passed after ledger append; no issues

## Not Run

- result: `PARTIAL`
- Live backend runtime smoke was not run.
- DB, Qdrant, Redis, news stores, memory stores, source PDFs, extraction outputs,
  prompts, gold labels, runtime/model/GPU/service config, and production data
  were not mutated.
