---
job_id: issue249_legacy_chat_route_auth_guard_current_base_v1_20260628
title: Gate legacy chat route before model or strategy execution
lane: Query Orchestration
supporting_lanes:
  - Reporting
  - Runtime
  - Provenance
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 2400
output_dir: reports/agent_jobs/issue249_legacy_chat_route_auth_guard_current_base_v1_20260628
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
allowed_files:
  - docs/agent_tasks/issue249_legacy_chat_route_auth_guard_current_base_v1_20260628.md
  - financial-engine_v2/backend/app/api/auth.py
  - financial-engine_v2/backend/app/api/routes.py
  - financial-engine_v2/backend/app/routes/chat.py
  - financial-engine_v2/backend/tests/test_chat_route.py
  - financial-engine_v2/backend/tests/test_local_api_key.py
  - reports/agent_jobs/issue249_legacy_chat_route_auth_guard_current_base_v1_20260628/README.md
  - reports/agent_jobs/issue249_legacy_chat_route_auth_guard_current_base_v1_20260628/VALIDATION.md
  - reports/agent_jobs/issue249_legacy_chat_route_auth_guard_current_base_v1_20260628/REVIEW.md
  - reports/agent_jobs/issue249_legacy_chat_route_auth_guard_current_base_v1_20260628/PR_BODY.md
  - reports/agent_jobs/issue249_legacy_chat_route_auth_guard_current_base_v1_20260628/status.json
  - reports/agent_jobs/issue249_legacy_chat_route_auth_guard_current_base_v1_20260628/diff-check.json
docs_impact: DOCS_NOT_REQUIRED
docs_checked:
  - AGENTS.md
  - docs/README.md
  - docs/dev_flow/REPO_PATH_OWNERSHIP_AND_WORK_PRESERVATION.md
docs_changed: []
docs_followup: NONE
reason: "Issue #249: legacy POST /chat and /api/chat must require the configured local API key before model, session-memory, or strategy-controller side effects."
task_tier: medium
recommended_model: "standard coding model"
actual_model: "Codex GPT-5"
why_this_model: "The fix is a narrow FastAPI dependency update plus focused auth regression tests."
worker_model_allowed: false
worker_decision_limit: "no worker; main orchestrator only"
escalation_needed: false
---

# Issue 249 Legacy Chat Route Auth Guard

## Objective

Guard the legacy chat router mounted at `POST /chat` and `POST /api/chat`
with the existing local API-key dependency when `settings.local_api_key` is
configured.

## Scope

Allowed:

- Add the existing `require_api_key` dependency to the legacy chat route.
- Move the existing `require_api_key` helper into a lightweight auth module
  while preserving the `app.api.routes.require_api_key` import surface.
- Add focused negative-path tests proving missing or wrong keys reject before
  analysis-mode model/session side effects and strategy-mode controller side
  effects.
- Add a focused positive-path test proving matching keys preserve legacy
  analysis behavior.
- Add route registration coverage for both mounted legacy paths.
- Record validation and review artifacts under this job report directory.

Forbidden:

- No route removal, deprecation, broad chat ownership changes, or source/evidence
  envelope changes.
- No product runtime, DB, Qdrant, Redis, news, memory, extraction, prompt,
  parser, gold-label, source PDF, model, GPU, service, package, or lockfile
  mutation.
- No unrelated backend/Cockpit refactor.
- No merge, rebase, reset, stash, clean, branch deletion, issue closeout, or
  production/runtime write actions.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue249_legacy_chat_route_auth_guard_current_base_v1_20260628.md`
- Focused backend pytest for:
  - `financial-engine_v2/backend/tests/test_chat_route.py`
  - `financial-engine_v2/backend/tests/test_local_api_key.py`
- `uv run --with ruff ruff check financial-engine_v2/backend/app/api/auth.py financial-engine_v2/backend/app/api/routes.py financial-engine_v2/backend/app/routes/chat.py financial-engine_v2/backend/tests/test_chat_route.py financial-engine_v2/backend/tests/test_local_api_key.py`
- `python3 -m py_compile financial-engine_v2/backend/app/api/auth.py financial-engine_v2/backend/app/api/routes.py financial-engine_v2/backend/app/routes/chat.py financial-engine_v2/backend/tests/test_chat_route.py financial-engine_v2/backend/tests/test_local_api_key.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/issue249_legacy_chat_route_auth_guard_current_base_v1_20260628.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/issue249_legacy_chat_route_auth_guard_current_base_v1_20260628.md --repo-root .`

## Done Criteria

- Both mounted legacy paths reject missing or wrong API keys before analysis and
  strategy side effects when `settings.local_api_key` is configured.
- Matching API key still allows legacy analysis behavior.
- Diff remains inside `allowed_files`.
- PR is opened if validation gates allow it.
