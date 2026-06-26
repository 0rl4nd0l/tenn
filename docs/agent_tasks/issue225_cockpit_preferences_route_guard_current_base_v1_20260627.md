---
job_id: issue225_cockpit_preferences_route_guard_current_base_v1_20260627
lane: Reporting
supporting_lanes:
  - Query Orchestration
  - Runtime
  - Evaluation
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/issue225_cockpit_preferences_route_guard_current_base_v1_20260627.md
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/tests/test_cockpit_api_preferences.py
  - financial-engine_v2/backend/tests/test_local_api_key.py
  - cockpit-ui/lib/api-client.ts
  - cockpit-ui/lib/api-client.test.ts
  - docs/architecture/19_backend_api_surface.md
  - reports/agent_jobs/issue225_cockpit_preferences_route_guard_current_base_v1_20260627/README.md
  - reports/agent_jobs/issue225_cockpit_preferences_route_guard_current_base_v1_20260627/STATE.md
  - reports/agent_jobs/issue225_cockpit_preferences_route_guard_current_base_v1_20260627/VALIDATION.md
  - reports/agent_jobs/issue225_cockpit_preferences_route_guard_current_base_v1_20260627/REVIEW.md
  - reports/agent_jobs/issue225_cockpit_preferences_route_guard_current_base_v1_20260627/PR_BODY.md
  - reports/agent_jobs/issue225_cockpit_preferences_route_guard_current_base_v1_20260627/status.json
  - reports/agent_jobs/issue225_cockpit_preferences_route_guard_current_base_v1_20260627/validation.json
  - reports/agent_jobs/issue225_cockpit_preferences_route_guard_current_base_v1_20260627/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/issue225_cockpit_preferences_route_guard_current_base_v1_20260627
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
docs_impact: DOCS_UPDATED
docs_checked:
  - AGENTS.md
  - docs/README.md
  - docs/architecture/19_backend_api_surface.md
  - issue #225
docs_changed:
  - docs/architecture/19_backend_api_surface.md
docs_followup: NONE
reason: "Issue #225 changes the access contract for Cockpit routing preference mutations."
task_tier: medium
recommended_model: "standard coding model"
actual_model: "Codex GPT-5"
why_this_model: "Focused backend route guard with small frontend header continuity update."
worker_model_allowed: false
worker_decision_limit: "No workers used; the issue is narrow and route-local."
escalation_needed: false
related_issue: 225
---

# Cockpit Preferences Route Guard

## Objective

Close issue #225 from current canonical by requiring the configured local API key
before Cockpit routing preferences can be changed, while keeping authenticated
Settings UI preference updates working.

## Existing Work Classification

- `CONTINUE`: issue #225 is open and ready.
- `NO_MATCHING_ACTIVE_WORK_FOUND`: guard preflight and focused GitHub PR search
  found no matching active PR for the Cockpit preferences route guard.
- `PRESERVE`: preference semantics, validation, chat controller refresh, and
  runtime/config defaults remain unchanged; this task only adds the operator
  access boundary and client header continuity.

## Scope

- Add an API-key dependency to direct backend `PATCH /api/cockpit/preferences`.
- Keep `GET /api/cockpit/preferences` behavior unchanged.
- Add focused backend tests proving missing/wrong keys are denied before state
  mutation and matching keys preserve preference updates.
- Preserve invalid-value rejection for routing policy and runtime target values.
- Send the configured Cockpit API key from the preference client patch path.
- Add focused API-client coverage for preference patch header propagation.
- Document the guarded mutation contract in the backend API surface note.

## Hard Stops

- Do not mutate production DB, Qdrant, Redis, news stores, memory stores, source
  PDFs, extraction outputs, prompts, gold labels, runtime/model/GPU/service
  config, or production data.
- Do not change launcher defaults, model config, runtime service config,
  preference keys, preference values, or chat routing semantics.
- Do not broaden into all Cockpit route auth, route aliases, holdings/watchlist,
  marketplace state, or action-control surfaces.
- Stop if implementation requires production data access or active ownership on
  `financial-engine_v2/backend/app/routes/cockpit_api.py`.

## Validation

- Task-card validate.
- Registry overlap check and claim.
- Ledger claimed and implementation state entries.
- RED focused pytest before implementation.
- GREEN focused pytest after implementation.
- Focused Vitest for the touched API client path.
- Targeted Ruff check for touched Python files.
- `python3 -m py_compile` on touched Python files.
- `git diff --check`.
- Task-card `check-diff`, `check-report-artifacts`, and `check-closeout`.
