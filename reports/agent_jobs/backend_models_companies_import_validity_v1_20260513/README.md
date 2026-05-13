# Backend Models Companies Import Validity

verdict: partial

## Scope

- branch: `codex/backend-models-companies-import-validity-v1-20260513`
- HEAD: `7916e685e57b` before commit
- worktree: `/home/l4nd0/tenn-backend-models-companies-import-validity-v1-20260513`
- lane: Evaluation
- execution mode: SAFE EXTENSION
- collision risk: MEDIUM by task card; clean-worktree execution with registry claim reduced practical overlap risk
- task card: `docs/agent_tasks/backend_models_companies_import_validity_v1_20260513.md`

## Task Card And Registry

- Task card created before backend source/test changes.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/backend_models_companies_import_validity_v1_20260513.md`: ok.
- Original requested NVMe worktree `/home/l4nd0/tenn-fast-dev-storage-v1` was blocked by an unrelated dirty task card outside `allowed_files`.
- Clean NVMe sibling worktree created from the same HEAD to satisfy the overlap gate.
- `python3 scripts/agent_job_registry.py list-active`: no active jobs before claim.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/backend_models_companies_import_validity_v1_20260513.md`: ok in clean sibling worktree.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/backend_models_companies_import_validity_v1_20260513.md`: ok.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/backend_models_companies_import_validity_v1_20260513.md`: initial run rejected the README because the contract tool did not match the `reports/.../**` glob; task card was updated with the explicit README path; final run passed.
- `python3 scripts/agent_job_registry.py release backend_models_companies_import_validity_v1_20260513`: ok.

## Files Changed

- `docs/agent_tasks/backend_models_companies_import_validity_v1_20260513.md`
- `financial-engine_v2/backend/app/models/companies.py`
- `financial-engine_v2/backend/tests/test_models_import_contract.py`
- `reports/agent_jobs/backend_models_companies_import_validity_v1_20260513/README.md`

## Root Cause

`financial-engine_v2/backend/app/models/__init__.py`, `app.providers.universe`, and `app.services.cockpit_service` import `app.models.companies.Company`, but `financial-engine_v2/backend/app/models/companies.py` was absent in this checkout. The expected ORM shape was not ambiguous because Alembic migration `0007_add_companies_table.py` defines the `companies` table schema.

The repo root `.gitignore` still has a broad `models/` rule that ignores `financial-engine_v2/backend/app/models/companies.py`; this task card did not allow editing `.gitignore`, so the model file must be force-added when committing.

## Why The Fix Is Narrow

The source change only restores the missing SQLAlchemy `Company` model with columns, primary key, unique constraints, and index matching migration `0007_add_companies_table.py`. It does not alter runtime launch/config files, Docker, databases, memory stores, Qdrant, extraction, retrieval, source/provenance logic, QueryOrchestrator, chat routes, or Cockpit UI.

The new test only checks the backend model import contract and schema metadata; it does not change production behavior.

## Validation

- `PYTHONPATH="$PWD/financial-engine_v2/backend:$PWD/financial-engine_v2" /mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python - <<'PY' ...`: passed, printed `backend_import_ok`.
- `PYTHONPATH="$PWD/financial-engine_v2/backend:$PWD/financial-engine_v2" /mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_models_import_contract.py -q`: passed, `3 passed`.
- `PYTHONPATH="$PWD/financial-engine_v2/backend:$PWD/financial-engine_v2" /mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_pipeline_stages.py -q`: passed, `23 passed`.
- `PYTHONPATH="$PWD/financial-engine_v2/backend:$PWD/financial-engine_v2" /mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_rag_payload_guardrails.py -q`: collected and ran, but failed with `3 failed, 8 passed`.
- `PYTHONPATH="$PWD/financial-engine_v2/backend:$PWD/financial-engine_v2" /mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python -m ruff check financial-engine_v2/backend/app/models/companies.py financial-engine_v2/backend/tests/test_models_import_contract.py`: passed.
- `git diff --check`: passed.
- `git diff --cached --check`: passed.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/backend_models_companies_import_validity_v1_20260513.md`: passed.

## Import Status

- `app.models`: imports now.
- `app.main`: imports now.

## Required Test Status

- `test_pipeline_stages.py`: collects and passes.
- `test_rag_payload_guardrails.py`: collects after the import repair, then fails in existing `process_document` behavior assertions:
  - `test_process_document_deletes_existing_points_before_upsert`
  - `test_process_document_skips_invalid_chunk_payloads`
  - `test_process_document_upserts_financial_rows_for_ok_low_confidence`

These failures are outside the narrow `app.models.companies` import repair. Fixing them would require changing pipeline behavior or broader test expectations beyond this import-contract task.

## Remaining Blockers

- `test_rag_payload_guardrails.py` has three non-import behavioral failures after collection succeeds.
- The requested original worktree `/home/l4nd0/tenn-fast-dev-storage-v1` remains blocked for this task-card workflow by unrelated dirty file `docs/agent_tasks/runtime_topology_nvme_backend_cockpit_cached_start_v1_20260513.md`.
- `.gitignore` still ignores `financial-engine_v2/backend/app/models/companies.py`; this task worked around that with force-add only.

## DATA_MISSING

- `graphify-out/wiki/index.md` and `graphify-out/GRAPH_REPORT.md` were not present in this checkout.
- The clean sibling worktree did not have `financial-engine_v2/.venv`; validation used the existing `/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python` interpreter with `PYTHONPATH` pointed at this worktree.

## Runtime Retry

The next runtime cached-start task can be retried after this branch is integrated into the NVMe runtime source tree. It should not be retried from the original fast worktree until the model file is present there and the unrelated task-card dirt is handled or isolated.

## Final Git Status

Pre-commit status at report finalization had only allowed files staged:

- `A docs/agent_tasks/backend_models_companies_import_validity_v1_20260513.md`
- `A financial-engine_v2/backend/app/models/companies.py`
- `A financial-engine_v2/backend/tests/test_models_import_contract.py`
- `A reports/agent_jobs/backend_models_companies_import_validity_v1_20260513/README.md`

Final post-commit status is verified in the session closeout.

## Project Memory Save Recommendation

Save that the missing `app.models.companies` blocker is repaired by restoring a migration-matching `Company` ORM model, and that the root `.gitignore` broad `models/` rule can hide this file unless it is force-added or the ignore rule is narrowed in a separate authorized task.
