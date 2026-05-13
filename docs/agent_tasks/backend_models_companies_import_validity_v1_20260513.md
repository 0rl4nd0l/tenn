---
job_id: backend_models_companies_import_validity_v1_20260513
lane: Evaluation
owner: Codex
mutation_mode: safe_extension
approval_required: false
allow_unapproved_safe_extension: true
production_data_access: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/backend_models_companies_import_validity_v1_20260513
allowed_files:
  - docs/agent_tasks/backend_models_companies_import_validity_v1_20260513.md
  - financial-engine_v2/backend/app/models/__init__.py
  - financial-engine_v2/backend/app/models/companies.py
  - financial-engine_v2/backend/tests/test_models_import_contract.py
  - financial-engine_v2/backend/tests/test_pipeline_stages.py
  - financial-engine_v2/backend/tests/test_rag_payload_guardrails.py
  - reports/agent_jobs/backend_models_companies_import_validity_v1_20260513/README.md
  - reports/agent_jobs/backend_models_companies_import_validity_v1_20260513/**
---

# Task

Fix the narrow backend import/runtime startup blocker caused by `financial-engine_v2/backend/app/models/__init__.py` importing missing `app.models.companies`.

Primary lane: Evaluation
Supporting lanes: Runtime / Backend test validity / Repo Hygiene
Mode: SAFE EXTENSION
Expected collision risk: MEDIUM

# Context

This blocker is now confirmed in multiple places:

1. Runtime migration cached startup failed because `fe_backend` mounted the NVMe backend source and exited with:
   `ModuleNotFoundError: No module named 'app.models.companies'`.

2. Backend/Cockpit could not start from NVMe. `:8001` remains healthy, but `:8000`, `:8081`, and `:8002` are offline.

3. Earlier embedding/SQLite invariant and Memory cleanup validations also hit the same missing `app.models.companies` test-collection blocker.

Goal: repair the import contract narrowly so backend imports collect and cached NVMe backend startup can proceed in a later runtime task.

# Required preflight

Use the NVMe worktree:

`/home/l4nd0/tenn-fast-dev-storage-v1`

Run and report:

- date -Iseconds
- pwd
- git rev-parse --show-toplevel
- git branch --show-current
- git rev-parse --short=12 HEAD
- git status --short --untracked-files=all
- git worktree list
- python3 scripts/agent_job_contract.py validate docs/agent_tasks/backend_models_companies_import_validity_v1_20260513.md
- python3 scripts/agent_job_registry.py list-active
- python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/backend_models_companies_import_validity_v1_20260513.md
- claim task if safe

# Allowed work

Make the smallest safe source/test change to resolve the missing backend model import.

Allowed options:

1. Restore/add `financial-engine_v2/backend/app/models/companies.py` if the backend model package expects it.
2. Or adjust `financial-engine_v2/backend/app/models/__init__.py` if the import is stale and no companies model should exist.
3. Add a narrow import-contract test only if useful.
4. Update only directly relevant tests if they currently encode the stale import expectation.

# Explicitly forbidden

Do not modify:

- runtime launch/config files
- Dockerfiles or compose files
- product DBs or live data
- company_memory.sqlite
- Qdrant
- Postgres data
- news stores
- extraction prompts/parsers/gold labels
- QueryOrchestrator
- chat routes
- source-label/provenance logic
- Cockpit UI
- marketplace files
- memory cleanup code

Do not run live memory cleanup.
Do not run Docker build.
Do not start/fix `:8002`.

# Hard stops

Stop and report if:

- fixing `app.models.companies` requires broader schema/model redesign;
- the expected company model shape is ambiguous and no nearby tests/docs clarify it;
- dirty files overlap allowed surfaces;
- registry shows active overlapping backend/model work;
- production data access would be needed;
- resolving the import would require runtime/config changes.

# Validation required

Run, if available:

- `financial-engine_v2/.venv/bin/python - <<'PY'
import app.models
import app.main
print("backend_import_ok")
PY`

- `financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_pipeline_stages.py -q`

- `financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_rag_payload_guardrails.py -q`

- any new/updated import-contract test

- targeted ruff on changed Python files

- git diff --check

- task-card check-diff

- registry release

If `.venv` is not available in the NVMe worktree, use the repo-supported backend test invocation path, but do not create a new `.venv` or install dependencies unless a separate task authorizes it.

# Final report

Write:

reports/agent_jobs/backend_models_companies_import_validity_v1_20260513/README.md

Include:

- verdict: completed / partial / blocked
- branch / HEAD / worktree
- task card status
- registry claim/release status
- exact files changed
- root cause of missing `app.models.companies`
- why the chosen fix is narrow
- exact tests run and results
- whether `app.models` and `app.main` import now
- whether `test_pipeline_stages.py` and `test_rag_payload_guardrails.py` collect/pass
- remaining blockers
- DATA_MISSING
- final git status
- whether the next runtime cached-start task can be retried
- Project Memory save recommendation
