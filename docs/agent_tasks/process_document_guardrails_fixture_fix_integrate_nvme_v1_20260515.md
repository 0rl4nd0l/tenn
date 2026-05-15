---
job_id: process_document_guardrails_fixture_fix_integrate_nvme_v1_20260515
lane: Evaluation
owner: Codex
mutation_mode: safe_extension
approval_required: true
approval_id: USER_APPROVED_PROCESS_DOCUMENT_GUARDRAILS_FIXTURE_FIX_INTEGRATE_NVME_20260515_GPT
production_data_access: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/process_document_guardrails_fixture_fix_integrate_nvme_v1_20260515
allowed_files:
  - docs/agent_tasks/process_document_guardrails_fixture_fix_integrate_nvme_v1_20260515.md
  - financial-engine_v2/backend/tests/test_rag_payload_guardrails.py
  - reports/agent_jobs/process_document_guardrails_fixture_fix_integrate_nvme_v1_20260515/README.md
  - reports/agent_jobs/process_document_guardrails_fixture_fix_integrate_nvme_v1_20260515/status.json
  - reports/agent_jobs/process_document_guardrails_fixture_fix_integrate_nvme_v1_20260515/diff-check.json
---

# Task

Integrate the completed `process_document` RAG payload guardrail fixture fix into the active NVMe branch.

Primary lane: Evaluation
Supporting lanes: Repo Hygiene
Mode: SAFE EXTENSION
Expected collision risk: LOW/MEDIUM

# Context

The fix was completed in isolated worktree:

- Branch: `safe/process-document-rag-guardrails-fixture-fix-v1-20260515`
- Worktree: `/home/l4nd0/tenn-process-document-rag-guardrails-fixture-fix-v1-20260515`
- Commit: `5037f385c037`
- Subject: `milestone(evaluation): align process_document rag guardrail fixtures`

Validation passed there:

- `backend_import_ok`
- `test_rag_payload_guardrails.py`: 11 passed
- `test_pipeline_stages.py`: 23 passed
- `test_models_import_contract.py`: 3 passed
- targeted Ruff passed
- git diff/check-diff passed
- no production code changed

Goal:
Bring this test-only fixture fix into `/home/l4nd0/tenn-fast-dev-storage-v1`.

# Required preflight

Run from:

`/home/l4nd0/tenn-fast-dev-storage-v1`

Commands:

- date -Iseconds
- pwd
- git rev-parse --show-toplevel
- git branch --show-current
- git rev-parse --short=12 HEAD
- git status --short --untracked-files=all
- git worktree list
- python3 scripts/agent_job_contract.py validate docs/agent_tasks/process_document_guardrails_fixture_fix_integrate_nvme_v1_20260515.md
- python3 scripts/agent_job_registry.py list-active
- python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/process_document_guardrails_fixture_fix_integrate_nvme_v1_20260515.md
- claim task if safe
- verify source commit:
  - git show --stat --oneline --decorate --no-renames 5037f385c037

# Integration method

Preferred:

`git cherry-pick --no-commit 5037f385c037`

Then keep only:

- `financial-engine_v2/backend/tests/test_rag_payload_guardrails.py`

Do not bring over the old task card/report artifacts from the source branch. This integration task will have its own task card/report.

If cherry-pick conflicts outside the allowed test file, stop and report.

# Explicitly forbidden

Do not edit:

- production code
- `process_document`
- extraction implementation
- embedding/vector/Qdrant code
- SQLite/canonical financial truth code
- QueryOrchestrator
- source-label/provenance code
- Cockpit/Home/UI
- runtime scripts
- Docker/compose
- DBs/Qdrant/Postgres/news/company memory

# Required validation

Use dependency-ready interpreter.

Preferred:

`/home/l4nd0/tenn-fast-dev-storage-v1/financial-engine_v2/.venv/bin/python`

Fallback:

`/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python`

Use:

`PYTHONPATH="$PWD/financial-engine_v2/backend:$PWD/financial-engine_v2"`

Run:

```bash
PYTHONPATH="$PWD/financial-engine_v2/backend:$PWD/financial-engine_v2" <python> - <<'PY'
import app.models
import app.main
print("backend_import_ok")
PY

PYTHONPATH="$PWD/financial-engine_v2/backend:$PWD/financial-engine_v2" <python> -m pytest financial-engine_v2/backend/tests/test_rag_payload_guardrails.py -q
PYTHONPATH="$PWD/financial-engine_v2/backend:$PWD/financial-engine_v2" <python> -m pytest financial-engine_v2/backend/tests/test_pipeline_stages.py -q
PYTHONPATH="$PWD/financial-engine_v2/backend:$PWD/financial-engine_v2" <python> -m pytest financial-engine_v2/backend/tests/test_models_import_contract.py -q
PYTHONPATH="$PWD/financial-engine_v2/backend:$PWD/financial-engine_v2" <python> -m ruff check financial-engine_v2/backend/tests/test_rag_payload_guardrails.py
```

Final checks:

```bash
git diff --check
git diff --cached --check
python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/process_document_guardrails_fixture_fix_integrate_nvme_v1_20260515.md
python3 scripts/agent_job_registry.py release process_document_guardrails_fixture_fix_integrate_nvme_v1_20260515
python3 scripts/agent_job_registry.py list-active
git status --short --untracked-files=all
```

# Commit rules

Commit only if:

- only the allowed test file plus this task/report artifacts are staged
- validation passes
- no production code changed

Suggested commit:

`milestone(evaluation): integrate process_document guardrail fixture fix`

# Final report

Write:

`reports/agent_jobs/process_document_guardrails_fixture_fix_integrate_nvme_v1_20260515/README.md`

Include:

- verdict
- branch / HEAD / worktree
- source commit
- files changed
- validation results
- production behavior impact
- final git status
- registry release/list-active
- Project Memory save recommendation
