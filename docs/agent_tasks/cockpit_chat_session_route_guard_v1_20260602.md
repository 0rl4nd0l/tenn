---
job_id: cockpit_chat_session_route_guard_v1_20260602
lane: Query Orchestration
supporting_lanes:
  - Reporting
  - Runtime
  - Provenance
  - Evaluation
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_chat_session_route_guard_v1_20260602.md
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/tests/test_cockpit_api_chat_sessions.py
  - financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py
  - financial-engine_v2/backend/tests/test_cockpit_api_chat_stream_keepalive.py
  - financial-engine_v2/backend/tests/test_local_api_key.py
  - cockpit-ui/lib/api-client.ts
  - cockpit-ui/lib/api-client.test.ts
  - reports/agent_jobs/cockpit_chat_session_route_guard_v1_20260602/README.md
  - reports/agent_jobs/cockpit_chat_session_route_guard_v1_20260602/STATE.md
  - reports/agent_jobs/cockpit_chat_session_route_guard_v1_20260602/VALIDATION.md
  - reports/agent_jobs/cockpit_chat_session_route_guard_v1_20260602/REVIEW.md
  - reports/agent_jobs/cockpit_chat_session_route_guard_v1_20260602/PR_BODY.md
  - reports/agent_jobs/cockpit_chat_session_route_guard_v1_20260602/status.json
  - reports/agent_jobs/cockpit_chat_session_route_guard_v1_20260602/validation.json
  - reports/agent_jobs/cockpit_chat_session_route_guard_v1_20260602/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_chat_session_route_guard_v1_20260602
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
docs_impact: NO_DOCS_CHANGE
docs_checked:
  - AGENTS.md
  - docs/README.md
  - issue #229
docs_changed: []
docs_followup: NONE
reason: "Issue #229 changes the direct backend access contract and Cockpit browser API-key forwarding for core chat/session routes."
task_tier: medium
recommended_model: "standard coding model"
actual_model: "Codex GPT-5"
why_this_model: "Focused backend route guard, client header forwarding, and regression tests for Cockpit chat/session authorization."
worker_model_allowed: false
worker_decision_limit: "No workers used; the issue is route-local after current duplicate checks found no matching PR or ledger claim."
escalation_needed: false
related_issue: 229
---

# Cockpit Chat Session Route Guard

## Objective

Close issue #229 from current canonical by requiring the configured local API
key before direct backend chat/session routes expose, mutate, or execute shared
Cockpit chat state, while preserving the normal Cockpit browser path by
forwarding the configured key from `cockpit-ui/lib/api-client.ts`.

## Existing Work Classification

- `CONTINUE`: issue #229 is open and ready.
- `NO_MATCHING_ACTIVE_WORK_FOUND`: current guard preflight, live ledger search,
  focused GitHub PR search, and issue comments found no active PR or claim for
  this exact chat/session route guard.
- `PRESERVE`: adjacent chat work remains out of scope, including attachment
  upload, legacy chat-route ownership, action-control routes, and evidence
  envelope behavior.

## Scope

- Add API-key dependencies to direct backend `/api/cockpit/chat/sessions` list
  and create routes.
- Add API-key dependencies to direct backend
  `/api/cockpit/chat/sessions/{session_id}` read and delete routes.
- Add API-key dependency to direct backend `POST /api/cockpit/chat`.
- Add negative-path backend tests proving missing/wrong keys are denied before
  chat execution, finalization, auto-flagging, or session mutation.
- Add authenticated backend tests proving list/create/read/delete, blocking
  chat, and SSE chat still work with the correct key.
- Add route-registration coverage for the newly guarded backend routes.
- Add focused API-client tests proving chat/session fetches and SSE streaming
  include `X-API-Key` when `NEXT_PUBLIC_API_KEY` is configured.

## Hard Stops

- Do not mutate production DB, Qdrant, Redis, news stores, memory stores, source
  PDFs, extraction outputs, prompts, gold labels, runtime/model/GPU/service
  config, or production data.
- Do not broaden into router-wide Cockpit auth, action-control routes,
  attachment upload, legacy chat route ownership, Prompt Lab, Marketplace,
  Strategy Lab, or route-alias behavior.
- Do not change chat persistence, evidence labeling, visible-source contracts,
  SSE payload semantics, or stateless-smoke behavior beyond enforcing the API
  key before request handling when configured.
- Stop if preserving the normal Cockpit web path requires a broad auth redesign
  or runtime/service changes.

## Validation

- Task-card validate.
- Registry overlap check and claim.
- Ledger claimed and implementation state entries.
- RED focused backend/Vitest checks before implementation.
- GREEN focused backend/Vitest checks after implementation.
- Targeted Ruff check for touched Python files.
- `python3 -m py_compile` on touched Python files.
- Focused frontend Vitest for `cockpit-ui/lib/api-client.test.ts`.
- `git diff --check`.
- Task-card `check-diff`, `check-report-artifacts`, and `check-closeout`.
