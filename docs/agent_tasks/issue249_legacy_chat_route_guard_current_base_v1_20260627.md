---
job_id: issue249_legacy_chat_route_guard_current_base_v1_20260627
lane: Query Orchestration
supporting_lanes:
  - Reporting
  - Runtime
  - Provenance
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/issue249_legacy_chat_route_guard_current_base_v1_20260627.md
  - financial-engine_v2/backend/app/routes/chat.py
  - financial-engine_v2/backend/tests/test_chat_route.py
  - financial-engine_v2/backend/tests/test_local_api_key.py
  - docs/architecture/19_backend_api_surface.md
  - reports/agent_jobs/issue249_legacy_chat_route_guard_current_base_v1_20260627/README.md
  - reports/agent_jobs/issue249_legacy_chat_route_guard_current_base_v1_20260627/STATE.md
  - reports/agent_jobs/issue249_legacy_chat_route_guard_current_base_v1_20260627/VALIDATION.md
  - reports/agent_jobs/issue249_legacy_chat_route_guard_current_base_v1_20260627/REVIEW.md
  - reports/agent_jobs/issue249_legacy_chat_route_guard_current_base_v1_20260627/PR_BODY.md
  - reports/agent_jobs/issue249_legacy_chat_route_guard_current_base_v1_20260627/status.json
  - reports/agent_jobs/issue249_legacy_chat_route_guard_current_base_v1_20260627/validation.json
  - reports/agent_jobs/issue249_legacy_chat_route_guard_current_base_v1_20260627/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/issue249_legacy_chat_route_guard_current_base_v1_20260627
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
docs_impact: DOCS_UPDATED
docs_checked:
  - AGENTS.md
  - docs/README.md
  - docs/architecture/19_backend_api_surface.md
  - issue #249
docs_changed:
  - docs/architecture/19_backend_api_surface.md
docs_followup: NONE
reason: "Issue #249 changes the access contract for POST /chat and POST /api/chat, so the backend API surface doc must mention the guard."
task_tier: medium
recommended_model: "standard coding model"
actual_model: "Codex GPT-5"
why_this_model: "Focused backend route guard with denial-before-side-effect regression tests."
worker_model_allowed: false
worker_decision_limit: "No workers used; the issue is narrow and backend-local."
escalation_needed: false
related_issue: 249
---

# Legacy Chat Route Auth Guard

## Objective

Close issue #249 from current canonical by requiring the configured local API key
before either legacy chat mount, `POST /chat` or `POST /api/chat`, can invoke
analysis-mode model/retrieval/session persistence or strategy-mode
proposal/confirm/apply behavior.

## Existing Work Classification

- `CONTINUE`: current issue #249 is open and ready.
- `NO_MATCHING_ACTIVE_WORK_FOUND`: fresh guard preflight and focused GitHub
  duplicate checks found no active PR or branch for this exact issue.
- `PRESERVE`: older legacy chat envelope and ownership work remains out of
  scope; this task only adds the auth guard and tests.

## Scope

- Add the existing `require_api_key` dependency to the legacy chat route.
- Add focused tests proving `/chat` and `/api/chat` reject missing or wrong keys
  before analysis side effects.
- Add focused tests proving `/chat` and `/api/chat` reject missing or wrong keys
  before strategy proposal/confirm/apply side effects.
- Preserve authenticated legacy behavior for analysis and strategy requests.
- Add route dependency coverage and update the backend API surface document.

## Hard Stops

- Do not mutate DB, Qdrant, Redis, news stores, memory stores, source PDFs,
  extraction outputs, prompts, gold labels, runtime/model/GPU/service config, or
  production data.
- Do not remove or deprecate `/chat` or `/api/chat`; ownership/deprecation
  belongs to #150/#171.
- Do not weaken source/evidence labels or provenance behavior.
- Do not broaden into Cockpit `/api/cockpit/chat` or session-route auth (#229).
- Stop if active ownership appears on `financial-engine_v2/backend/app/routes/chat.py`.

## Validation

- Task-card validate.
- Registry overlap check and claim.
- Ledger claimed and implementation state entries.
- RED focused pytest before implementation.
- GREEN focused pytest after implementation.
- Targeted Ruff check for touched Python files.
- `python3 -m py_compile` on touched Python files.
- `git diff --check`.
- Task-card `check-diff` and `check-report-artifacts`.
