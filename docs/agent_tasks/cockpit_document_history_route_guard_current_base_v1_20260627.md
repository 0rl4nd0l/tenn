---
job_id: cockpit_document_history_route_guard_current_base_v1_20260627
lane: Reporting
supporting_lanes:
  - Provenance
  - Evaluation
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_document_history_route_guard_current_base_v1_20260627.md
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/tests/test_local_api_key.py
  - financial-engine_v2/backend/tests/test_cockpit_docs_route_auth.py
  - cockpit-ui/lib/api-client.ts
  - cockpit-ui/lib/api-client.test.ts
  - docs/architecture/19_backend_api_surface.md
  - reports/agent_jobs/cockpit_document_history_route_guard_current_base_v1_20260627/README.md
  - reports/agent_jobs/cockpit_document_history_route_guard_current_base_v1_20260627/STATE.md
  - reports/agent_jobs/cockpit_document_history_route_guard_current_base_v1_20260627/VALIDATION.md
  - reports/agent_jobs/cockpit_document_history_route_guard_current_base_v1_20260627/REVIEW.md
  - reports/agent_jobs/cockpit_document_history_route_guard_current_base_v1_20260627/PR_BODY.md
  - reports/agent_jobs/cockpit_document_history_route_guard_current_base_v1_20260627/status.json
  - reports/agent_jobs/cockpit_document_history_route_guard_current_base_v1_20260627/validation.json
  - reports/agent_jobs/cockpit_document_history_route_guard_current_base_v1_20260627/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_document_history_route_guard_current_base_v1_20260627
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
docs_impact: DOCS_UPDATED
docs_checked:
  - AGENTS.md
  - docs/README.md
  - docs/architecture/19_backend_api_surface.md
  - issue #239
docs_changed:
  - docs/architecture/19_backend_api_surface.md
docs_followup: NONE
reason: "Issue #239 changes the access contract for GET /api/cockpit/docs, so the API surface doc must mention the guard."
task_tier: medium
recommended_model: "standard coding model"
actual_model: "Codex GPT-5"
why_this_model: "Focused backend route guard, API client header propagation, and tests."
worker_model_allowed: false
worker_decision_limit: "No workers used; stale local work is inspected and ported by the orchestrator."
escalation_needed: false
related_issue: 239
supersedes:
  - cockpit_document_history_route_guard_v1_20260626
---

# Cockpit Document History Route Guard

## Objective

Close issue #239 from current canonical by requiring the local API key on
`GET /api/cockpit/docs` when `settings.local_api_key` is configured, and by
making the Cockpit History client send the configured API key for document
history loads.

## Existing Work Classification

- `CONTINUE`: `/home/l4nd0/tenn-issue239-cockpit-doc-history-guard-v1-20260626`
  contains relevant uncommitted work on stale base
  `857e76c3180cb0b1fb9fc360652d6a9b64543c86`.
- The stale task card forbids push and issue closeout, so this current-base card
  supersedes it for implementation and PR closeout.
- Preserve the stale worktree untouched; port only the bounded useful changes.

## Scope

- Add the existing `require_api_key` dependency to the Cockpit docs route.
- Add backend route/auth coverage for unauthenticated denial and authenticated
  success on `/api/cockpit/docs`.
- Add `/api/cockpit/docs` to shared protected-route dependency coverage.
- Update `listDocuments()` to send the configured `X-API-Key` header.
- Add focused frontend API-client coverage that document history includes the
  auth header.
- Update the backend API surface doc for the guarded route contract.

## Hard Stops

- Do not mutate DB, Qdrant, Redis, news stores, memory stores, source PDFs,
  extraction outputs, prompts, gold labels, runtime/model/GPU/service config,
  or production data.
- Do not weaken source-PDF open or allowlist guards tracked by issue #155.
- Do not broaden into History timestamp rendering (#91/#160), shared browser
  API-key propagation beyond this client call (#232), or queue/runtime route
  guards (#230).
- Do not remove `pdf_path` from authenticated operator responses.
- Do not mutate or clean the stale #239 worktree.

## Validation

- Task-card validate.
- Registry overlap check and claim.
- Ledger claimed and implementation state entries.
- RED backend focused pytest before implementation.
- GREEN backend focused pytest after implementation.
- Focused frontend API-client test, or exact local dependency/tooling blocker.
- Targeted Ruff check for touched Python files.
- `python3 -m py_compile` on touched Python files.
- `git diff --check`.
- Task-card `check-diff` and `check-report-artifacts`.
