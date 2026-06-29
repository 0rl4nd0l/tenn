# Validation

## Passed

Post-rebase publication validation on 2026-06-29:

- `git rebase origin/migration/clean-runtime-baseline-reconstruct-v1`
  - exit 0
  - rebased branch onto `6c486d07743d3483d05fa163dc5c02fd66b68863`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/qdrant_physical_logical_vector_id_contract_shot2_v1_20260629.md`
  - exit 0
  - ok true
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/qdrant_physical_logical_vector_id_contract_shot2_v1_20260629.md --repo-root .`
  - exit 0
  - ok true
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
  - exit 0
  - `active_jobs=[]`
- `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_embeddings_local_point_id_compat.py financial-engine_v2/backend/tests/test_architecture_invariants.py financial-engine_v2/backend/tests/test_qdrant_resolution.py financial-engine_v2/backend/tests/test_rag_payload_guardrails.py -q`
  - exit 0
  - `62 passed`
- `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_pipeline_stages.py -q`
  - exit 0
  - `25 passed`
- `uv run --with ruff ruff check financial-engine_v2/backend/app/services/embeddings.py financial-engine_v2/backend/app/services/pipeline_stages.py financial-engine_v2/backend/app/services/commentary_ingest.py financial-engine_v2/backend/tests/test_embeddings_local_point_id_compat.py financial-engine_v2/backend/tests/test_architecture_invariants.py financial-engine_v2/backend/tests/test_qdrant_resolution.py financial-engine_v2/backend/tests/test_rag_payload_guardrails.py financial-engine_v2/scripts/inspect_qdrant_collection.py financial-engine_v2/scripts/embed_docs_to_qdrant.py`
  - exit 0
  - `All checks passed!`
- `python3 -m py_compile financial-engine_v2/backend/app/services/embeddings.py financial-engine_v2/backend/app/services/pipeline_stages.py financial-engine_v2/backend/app/services/commentary_ingest.py financial-engine_v2/scripts/inspect_qdrant_collection.py financial-engine_v2/scripts/embed_docs_to_qdrant.py`
  - exit 0
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/qdrant_physical_logical_vector_id_contract_shot2_v1_20260629.md --repo-root .`
  - exit 0
  - ok true
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/qdrant_physical_logical_vector_id_contract_shot2_v1_20260629.md --repo-root .`
  - exit 0
  - ok true
- `git diff --check`
  - exit 0

- `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /home/l4nd0/tenn-issue266-qdrant-vector-id-contract-shot2-v1-20260629 --topic "issue #266 qdrant physical logical vector id policy" --json`
  - exit 0
  - `final_decision=pass`
  - `path_ownership.classification=VALID_TASK_WORKTREE`
  - `duplicate_work_classification=NO_MATCHING_ACTIVE_WORK_FOUND`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/qdrant_physical_logical_vector_id_contract_shot2_v1_20260629.md`
  - exit 0
  - ok true
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/qdrant_physical_logical_vector_id_contract_shot2_v1_20260629.md --repo-root .`
  - exit 0
  - ok true
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/qdrant_physical_logical_vector_id_contract_shot2_v1_20260629.md --repo-root .`
  - exit 0 after registry claim refresh
- `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_embeddings_local_point_id_compat.py financial-engine_v2/backend/tests/test_architecture_invariants.py financial-engine_v2/backend/tests/test_qdrant_resolution.py financial-engine_v2/backend/tests/test_rag_payload_guardrails.py -q`
  - exit 0
  - `62 passed`
- `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_pipeline_stages.py -q`
  - exit 0
  - `25 passed`
- `uv run --with ruff ruff check financial-engine_v2/backend/app/services/embeddings.py financial-engine_v2/backend/app/services/pipeline_stages.py financial-engine_v2/backend/app/services/commentary_ingest.py financial-engine_v2/backend/tests/test_embeddings_local_point_id_compat.py financial-engine_v2/backend/tests/test_architecture_invariants.py financial-engine_v2/backend/tests/test_qdrant_resolution.py financial-engine_v2/backend/tests/test_rag_payload_guardrails.py financial-engine_v2/scripts/inspect_qdrant_collection.py financial-engine_v2/scripts/embed_docs_to_qdrant.py`
  - exit 0
  - `All checks passed!`
- `python3 -m py_compile financial-engine_v2/backend/app/services/embeddings.py financial-engine_v2/backend/app/services/pipeline_stages.py financial-engine_v2/backend/app/services/commentary_ingest.py financial-engine_v2/scripts/inspect_qdrant_collection.py financial-engine_v2/scripts/embed_docs_to_qdrant.py`
  - exit 0
- `git diff --check`
  - exit 0

## Not Run

- Live Qdrant inspector, reindex, rebuild, backfill, or service smoke.

Reason: forbidden by task scope without separate runtime/data approval.
