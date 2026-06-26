---
job_id: issue226_personal_portfolio_route_guard_current_base_v1_20260627
lane: Reporting
supporting_lanes:
  - Runtime
  - Provenance
  - Evaluation
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/issue226_personal_portfolio_route_guard_current_base_v1_20260627.md
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/tests/test_cockpit_api_watchlist.py
  - financial-engine_v2/backend/tests/test_cockpit_api_holdings.py
  - financial-engine_v2/backend/tests/test_local_api_key.py
  - docs/architecture/19_backend_api_surface.md
  - reports/agent_jobs/issue226_personal_portfolio_route_guard_current_base_v1_20260627/README.md
  - reports/agent_jobs/issue226_personal_portfolio_route_guard_current_base_v1_20260627/STATE.md
  - reports/agent_jobs/issue226_personal_portfolio_route_guard_current_base_v1_20260627/VALIDATION.md
  - reports/agent_jobs/issue226_personal_portfolio_route_guard_current_base_v1_20260627/REVIEW.md
  - reports/agent_jobs/issue226_personal_portfolio_route_guard_current_base_v1_20260627/PR_BODY.md
  - reports/agent_jobs/issue226_personal_portfolio_route_guard_current_base_v1_20260627/status.json
  - reports/agent_jobs/issue226_personal_portfolio_route_guard_current_base_v1_20260627/validation.json
  - reports/agent_jobs/issue226_personal_portfolio_route_guard_current_base_v1_20260627/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/issue226_personal_portfolio_route_guard_current_base_v1_20260627
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
docs_impact: DOCS_UPDATED
docs_checked:
  - AGENTS.md
  - docs/README.md
  - docs/architecture/19_backend_api_surface.md
  - issue #226
  - cockpit-ui holdings/watchlist/chat API-key call sites
docs_changed:
  - docs/architecture/19_backend_api_surface.md
docs_followup: NONE
reason: "Issue #226 changes the direct backend access contract for local personal holdings/watchlist state."
task_tier: medium
recommended_model: "standard coding model"
actual_model: "Codex GPT-5"
why_this_model: "Focused backend route guard and regression tests for personal Cockpit state routes."
worker_model_allowed: false
worker_decision_limit: "No workers used; the issue is route-local after current UI header paths were verified."
escalation_needed: false
related_issue: 226
---

# Personal Portfolio Route Guard

## Objective

Close issue #226 from current canonical by requiring the configured local API key
before direct backend holdings and watchlist read/write routes expose or mutate
local personal portfolio state.

## Existing Work Classification

- `CONTINUE`: issue #226 is open and ready.
- `NO_MATCHING_ACTIVE_WORK_FOUND`: fresh guard preflight, live ledger search,
  and focused GitHub PR search found no matching active PR for this route guard.
- `PRESERVE`: current Cockpit Holdings, Watchlist, and chat-side watchlist-add
  browser paths already send `X-API-Key`; this task preserves those paths and
  only closes the direct backend route boundary.

## Scope

- Add API-key dependencies to direct backend `/api/cockpit/watchlist` list,
  create, and delete routes.
- Add API-key dependencies to direct backend `/api/cockpit/holdings` list,
  create, update, and delete routes.
- Keep existing holdings/watchlist semantics unchanged for authenticated calls.
- Add focused backend tests proving missing/wrong keys are denied and rejected
  create/update/delete requests do not mutate state.
- Add focused backend tests proving matching keys preserve list/create/update/
  delete behavior.
- Add shared route-registration coverage for each newly guarded route.
- Document the guarded local-personal-data route contract.

## Current UI Header Evidence

No frontend changes are required in this lane because current canonical already
sends `X-API-Key` from the configured Cockpit API key path:

- `cockpit-ui/components/cockpit/holdings/holdings-screen.tsx`
- `cockpit-ui/components/cockpit/watchlist/watchlist-screen.tsx`
- `cockpit-ui/components/cockpit/chat/chat-screen.tsx`

The BFF routes under `cockpit-ui/app/api/cockpit/holdings*` and
`cockpit-ui/app/api/cockpit/watchlist*` forward request headers to the backend.

## Hard Stops

- Do not mutate production DB, Qdrant, Redis, news stores, memory stores, source
  PDFs, extraction outputs, prompts, gold labels, runtime/model/GPU/service
  config, or production data.
- Do not change holdings/watchlist storage semantics, source-label semantics,
  financial-truth status, or chat evidence labeling.
- Do not broaden into marketplace state, route aliases, action controls, or all
  Cockpit auth without a separate task card.
- Stop if implementation requires frontend behavior changes beyond preserving
  the already-present API-key header path.

## Validation

- Task-card validate.
- Registry overlap check and claim.
- Ledger claimed and implementation state entries.
- RED focused pytest before implementation.
- GREEN focused pytest after implementation.
- Targeted Ruff check for touched Python files.
- `python3 -m py_compile` on touched Python files.
- `git diff --check`.
- Task-card `check-diff`, `check-report-artifacts`, and `check-closeout`.
