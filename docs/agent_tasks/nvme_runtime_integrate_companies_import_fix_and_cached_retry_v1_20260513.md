---
job_id: nvme_runtime_integrate_companies_import_fix_and_cached_retry_v1_20260513
lane: Evaluation
owner: Codex
mutation_mode: safe_extension
approval_required: true
approval_id: USER_APPROVED_INTEGRATE_COMPANIES_FIX_AND_RETRY_NVME_RUNTIME_20260513_GPT
production_data_access: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/nvme_runtime_integrate_companies_import_fix_and_cached_retry_v1_20260513
allowed_files:
  - docs/agent_tasks/nvme_runtime_integrate_companies_import_fix_and_cached_retry_v1_20260513.md
  - docs/agent_tasks/backend_models_companies_import_validity_v1_20260513.md
  - financial-engine_v2/backend/app/models/companies.py
  - financial-engine_v2/backend/tests/test_models_import_contract.py
  - reports/agent_jobs/backend_models_companies_import_validity_v1_20260513/README.md
  - reports/agent_jobs/nvme_runtime_integrate_companies_import_fix_and_cached_retry_v1_20260513/README.md
  - reports/agent_jobs/nvme_runtime_integrate_companies_import_fix_and_cached_retry_v1_20260513/**
  - docs/agent_tasks/runtime_topology_nvme_backend_cockpit_cached_start_v1_20260513.md
---

# Task

Integrate the committed `app.models.companies` import fix into the active NVMe runtime source tree, then retry cached backend/Cockpit startup without build.

Primary lane: Evaluation
Supporting lanes: Runtime / Backend import validity / Repo Hygiene
Mode: SAFE EXTENSION
Expected collision risk: MEDIUM

# Context

The narrow import repair succeeded in a clean sibling worktree:

- worktree: `/home/l4nd0/tenn-backend-models-companies-import-validity-v1-20260513`
- branch: `codex/backend-models-companies-import-validity-v1-20260513`
- commit: `2cc0f7180767 milestone(evaluation): restore backend companies model import`
- result: `app.models` and `app.main` import successfully
- validation passed:
  - backend import smoke passed
  - `test_models_import_contract.py`: 3 passed
  - `test_pipeline_stages.py`: 23 passed
  - targeted Ruff passed
  - diff/check-diff passed
- remaining non-import blocker:
  - `test_rag_payload_guardrails.py` now collects but fails 3 existing `process_document` behavior assertions

The active runtime tree is:

`/home/l4nd0/tenn-fast-dev-storage-v1`

It currently has `:8001` healthy from NVMe CWD, while `:8000`, `:8081`, and `:8002` are offline. A cached backend startup previously failed because the active NVMe source tree lacked `app.models.companies`.

# Required preflight

Run from `/home/l4nd0/tenn-fast-dev-storage-v1` unless noted:

- date -Iseconds
- pwd
- git rev-parse --show-toplevel
- git branch --show-current
- git rev-parse --short=12 HEAD
- git status --short --untracked-files=all
- git worktree list
- python3 scripts/agent_job_contract.py validate docs/agent_tasks/nvme_runtime_integrate_companies_import_fix_and_cached_retry_v1_20260513.md
- python3 scripts/agent_job_registry.py list-active
- python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/nvme_runtime_integrate_companies_import_fix_and_cached_retry_v1_20260513.md
- claim task if safe
- current listeners for :8000, :8001, :8081, :8002
- `curl -m 5 http://127.0.0.1:8001/health`
- `git show --stat --oneline --decorate --no-renames 2cc0f7180767 || true`

# Known dirty-file note

The active NVMe tree may contain this unrelated untracked task card:

`docs/agent_tasks/runtime_topology_nvme_backend_cockpit_cached_start_v1_20260513.md`

Do not edit or stage it unless it is already part of this task card's allowed-files handling. If it blocks overlap/check-diff despite being allowed, stop and report rather than deleting it.

# Allowed work

1. Integrate commit `2cc0f7180767` into `/home/l4nd0/tenn-fast-dev-storage-v1`.

Preferred method:
- `git cherry-pick 2cc0f7180767`

If cherry-pick is unavailable because the commit is not reachable from this worktree:
- apply the same minimal file changes from the sibling worktree, force-adding `financial-engine_v2/backend/app/models/companies.py` if required because the broad `.gitignore` `models/` rule ignores it.

2. Validate imports and focused tests.

3. Commit the integration in the active NVMe branch if the diff is clean and scoped.

4. Retry backend/Cockpit cached startup only after the import fix is present in this active NVMe tree.

Cached startup constraints:
- use existing images/cache only
- no `--build`
- no broad install
- no backend `.venv` creation
- keep current `:8001` as-is unless it regresses

# Explicitly forbidden

Do not modify:

- runtime launch/config files
- Dockerfiles or compose files
- QueryOrchestrator
- chat routes
- source-label/provenance logic
- Cockpit feature code
- marketplace code
- extraction prompts/parsers/gold labels
- company_memory.sqlite or memory cleanup code
- Qdrant data/config
- Postgres data
- news stores
- model weights/config/presets

Do not:
- run `docker compose up --build`
- run broad `pip install`
- create backend `.venv`
- fix `test_rag_payload_guardrails.py`
- change `process_document` behavior
- start/fix `:8002`
- run Memory Batch 5

# Hard stops

Stop and report if:

- cherry-pick conflicts outside the allowed files;
- the import fix requires broader schema/model redesign;
- `app.models` or `app.main` still fails after integration;
- cached backend startup requires image build;
- Cockpit requires dependency install;
- Docker compose wants destructive volume changes;
- current `:8001` regresses;
- active registry shows overlapping runtime/evaluation/backend work;
- any tracked product/source file outside allowed surfaces would need modification.

# Validation required after integration

Run, using the repo-supported interpreter path without creating a new venv:

- backend import smoke:
  `PYTHONPATH="$PWD/financial-engine_v2/backend:$PWD/financial-engine_v2" <python> - <<'PY'
import app.models
import app.main
print("backend_import_ok")
PY`

- `test_models_import_contract.py -q`
- `test_pipeline_stages.py -q`
- targeted Ruff on:
  - `financial-engine_v2/backend/app/models/companies.py`
  - `financial-engine_v2/backend/tests/test_models_import_contract.py`
- `git diff --check`
- task-card check-diff

Run `test_rag_payload_guardrails.py -q` only to confirm status, not to fix it. If it still fails the same 3 `process_document` behavior assertions, record as known separate blocker.

# Runtime retry after integration

Only after the import fix validates:

- run `docker compose up -d` from `/home/l4nd0/tenn-fast-dev-storage-v1/financial-engine_v2` without `--build`
- start Cockpit from `/home/l4nd0/tenn-fast-dev-storage-v1/cockpit-ui` only if dependencies already exist
- do not install dependencies
- do not rebuild images

# Runtime validation

Report:

- listeners for :8000, :8001, :8081, :8002
- process CWD/root evidence for backend, Cockpit, llama.cpp where available
- health probes:
  - `http://127.0.0.1:8000/api/health`
  - `http://127.0.0.1:8001/health`
  - `http://127.0.0.1:8001/v1/models`
  - `http://127.0.0.1:8081/api/cockpit/health`
  - `http://127.0.0.1:8081/api/cockpit/home` with timeout/latency/data_state if available
- Docker compose ps
- Docker volume preservation evidence
- final git status of NVMe and preserve worktrees
- registry release

# Final report

Write:

reports/agent_jobs/nvme_runtime_integrate_companies_import_fix_and_cached_retry_v1_20260513/README.md

Include:

- verdict: completed / partial / blocked / rolled back
- branch / HEAD / worktree
- whether `2cc0f7180767` was cherry-picked or manually applied
- exact files changed
- exact tests run and results
- whether `app.models` and `app.main` import in the active NVMe tree
- whether `test_rag_payload_guardrails.py` remains a separate blocker
- whether backend `:8000` starts from NVMe
- whether Cockpit `:8081` starts from NVMe
- whether `:8001` remained healthy
- Docker volume evidence
- rollback actions if used
- DATA_MISSING
- final git status
- next safe step
- Project Memory save recommendation
