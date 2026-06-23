---
job_id: repo_dev_import_runtime_entrypoint_remediation_v1_20260623
title: Repo dev import and runtime entrypoint remediation
lane: Evaluation
supporting_lanes:
  - Reporting
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/repo_dev_import_runtime_entrypoint_remediation_v1_20260623
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: false
allowed_files:
  - docs/agent_tasks/repo_dev_import_runtime_entrypoint_remediation_v1_20260623.md
  - reports/agent_jobs/repo_dev_import_runtime_entrypoint_remediation_v1_20260623/**
  - pyproject.toml
  - pytest.ini
  - financial-engine_v2/backend/tests/conftest.py
  - scripts/python_import_contract.py
  - scripts/test_python_import_contract.py
  - scripts/run_pytest_with_fallback.py
  - scripts/test_run_pytest_with_fallback.py
  - scripts/runtime_entrypoint_contract.py
  - scripts/test_runtime_entrypoint_contract.py
  - agent_contract.json
  - docs/entrypoints.md
  - docs/startup.md
docs_impact: DOCS_UPDATED
docs_checked:
  - docs/entrypoints.md
  - docs/startup.md
  - docs/validation_baseline.md
docs_changed:
  - docs/entrypoints.md
  - docs/startup.md
docs_followup: NONE
reason: "Implement first two repo architecture board recommendations: a deeper Python dev/test import module and a runtime entrypoint contract module."
task_tier: large
recommended_model: "high reasoning"
actual_model: "Codex GPT-5"
why_this_model: "The remediation crosses repo-level test import behavior, runtime docs, and validation contracts."
worker_model_allowed: true
worker_decision_limit: "bounded_implementation inside assigned allowed files only; orchestrator integrates and validates."
escalation_needed: false
---

# Repo Dev Import And Runtime Entrypoint Remediation

## Objective

Remediate the first two recommendations from
`reports/agent_jobs/repo_architecture_development_board_v1_20260623`:

1. Deepen the Python dev/test import module so tests and scripts stop depending
   on scattered path setup.
2. Deepen the runtime/startup entrypoint module so docs and machine-readable
   contract agree on the supported runtime modes.

## Scope

Allowed:

- Add a repo-level Python packaging/import contract or equivalent validation
  module.
- Keep existing validation fallback behavior while concentrating path rules in
  one import module.
- Add focused tests for import contract behavior.
- Add a runtime entrypoint contract/check module that validates docs and
  `agent_contract.json` against one source of truth.
- Reconcile `docs/entrypoints.md` and `docs/startup.md` wording without
  changing live runtime services.
- Write report-local worker results and validation notes under the output
  directory.

Forbidden:

- No product runtime, DB, Qdrant, Redis, news, memory, source-PDF, gold-label,
  model, GPU, systemd host, Docker host, cron, or `.env` mutation.
- No dependency lockfile, CI, system package, production venv, or host-global
  config changes.
- No broad Cockpit, extraction, RAG, news, or control-plane cleanup outside the
  exact allowed files.
- No GitHub mutation, merge, rebase, reset, stash, clean, force-push, branch
  deletion, or worktree deletion.

## Worker Lanes

### Worker A: Python Dev/Test Import Module

Allowed write files:

- `pyproject.toml`
- `pytest.ini`
- `financial-engine_v2/backend/tests/conftest.py`
- `scripts/python_import_contract.py`
- `scripts/test_python_import_contract.py`
- `scripts/run_pytest_with_fallback.py`
- `scripts/test_run_pytest_with_fallback.py`
- `reports/agent_jobs/repo_dev_import_runtime_entrypoint_remediation_v1_20260623/worker_import/WORKER_RESULT.md`

Stop if the fix requires dependency lockfile changes, production venv mutation,
or broad test-tree rewrites.

### Worker B: Runtime Entrypoint Module

Allowed write files:

- `scripts/runtime_entrypoint_contract.py`
- `scripts/test_runtime_entrypoint_contract.py`
- `agent_contract.json`
- `docs/entrypoints.md`
- `docs/startup.md`
- `reports/agent_jobs/repo_dev_import_runtime_entrypoint_remediation_v1_20260623/worker_runtime/WORKER_RESULT.md`

Stop if the fix requires runtime/service mutation, Docker/systemd/cron edits,
or changing actual port/start behavior instead of validating/reconciling the
contract.

## Required Preflight

1. Record worktree, branch, HEAD, selected base, and `git status`.
2. Validate this task card.
3. Run registry `list-active --read-only`.
4. Run task ledger validation and duplicate-work search.
5. Confirm no active sibling worktree has dirty overlapping files.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/repo_dev_import_runtime_entrypoint_remediation_v1_20260623.md`
- `python3 scripts/test_python_import_contract.py`
- `python3 scripts/test_runtime_entrypoint_contract.py`
- `python3 scripts/test_run_pytest_with_fallback.py`
- `python3 scripts/run_pytest_with_fallback.py --base-python "$(command -v python3)" -- scripts/test_python_import_contract.py scripts/test_runtime_entrypoint_contract.py -q`
- `python3 -m py_compile scripts/python_import_contract.py scripts/runtime_entrypoint_contract.py scripts/run_pytest_with_fallback.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/repo_dev_import_runtime_entrypoint_remediation_v1_20260623.md`

## Done Criteria

- Import/path rules have a single tested module-level interface.
- Runtime startup docs no longer contradict each other.
- `agent_contract.json` and docs are validated by a focused contract test.
- Worker results and orchestrator closeout record validation, docs impact, and
  remaining risks.
