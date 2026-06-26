---
job_id: cockpit_marketplace_state_route_guard_v1_20260602
lane: Reporting
supporting_lanes:
  - Runtime
  - Evaluation
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_marketplace_state_route_guard_v1_20260602.md
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/tests/test_cockpit_marketplace_api.py
  - financial-engine_v2/backend/tests/test_local_api_key.py
  - reports/agent_jobs/cockpit_marketplace_state_route_guard_v1_20260602/README.md
  - reports/agent_jobs/cockpit_marketplace_state_route_guard_v1_20260602/STATE.md
  - reports/agent_jobs/cockpit_marketplace_state_route_guard_v1_20260602/VALIDATION.md
  - reports/agent_jobs/cockpit_marketplace_state_route_guard_v1_20260602/REVIEW.md
  - reports/agent_jobs/cockpit_marketplace_state_route_guard_v1_20260602/PR_BODY.md
  - reports/agent_jobs/cockpit_marketplace_state_route_guard_v1_20260602/status.json
  - reports/agent_jobs/cockpit_marketplace_state_route_guard_v1_20260602/validation.json
  - reports/agent_jobs/cockpit_marketplace_state_route_guard_v1_20260602/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_marketplace_state_route_guard_v1_20260602
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
docs_impact: NO_DOCS_CHANGE
docs_checked:
  - AGENTS.md
  - docs/README.md
  - issue #227
docs_changed: []
docs_followup: NONE
reason: "Issue #227 protects Cockpit Marketplace operator state routes from unauthenticated direct backend access."
task_tier: medium
recommended_model: "standard coding model"
actual_model: "Codex GPT-5"
why_this_model: "Focused backend route guard and regression tests for Marketplace mission/match/alert state routes."
worker_model_allowed: false
worker_decision_limit: "No workers used; the issue is route-local after duplicate checks found no matching PR or ledger claim."
escalation_needed: false
related_issue: 227
---

# Cockpit Marketplace State Route Guard

## Objective

Close issue #227 from current canonical by requiring the configured local API
key before direct backend Cockpit Marketplace mission, match, benchmark-review,
feedback, and alert state routes expose or mutate operator workflow state.

## Existing Work Classification

- `CONTINUE`: issue #227 is open and ready.
- `NO_MATCHING_ACTIVE_WORK_FOUND`: current guard preflight, live ledger search,
  focused GitHub PR search, and issue comments found no active PR or claim for
  this exact Marketplace state route guard.
- `PRESERVE`: issue #121 remains adjacent for explicit action-control launch
  and stop routes. This task does not remediate marketplace scan, calibration,
  eBay sync, or broad action-control routes.

## Current Frontend Header Evidence

No frontend source change is required in this lane. Current canonical already
threads the browser API key into Marketplace helpers through `apiKey` function
arguments and `buildHeaders(...)`, and Marketplace BFF route tests already prove
header passthrough for mission and match paths.

## Scope

- Add API-key dependencies to direct backend Marketplace mission list/create/
  read/update/link/unlink/delete routes.
- Add API-key dependencies to direct backend Marketplace match list/read/status
  update/feedback/benchmark-review routes.
- Add API-key dependencies to direct backend Marketplace alert list/update
  routes.
- Add focused backend tests proving missing/wrong keys are denied and rejected
  mission create/update, match feedback/status, benchmark-review, and alert
  update requests do not mutate state or trigger mission warm-up side effects.
- Add authenticated backend tests proving existing Marketplace workflows still
  work with the correct key.
- Add route-registration coverage for newly guarded routes.

## Hard Stops

- Do not mutate production DB, Qdrant, Redis, news stores, memory stores, source
  PDFs, extraction outputs, prompts, gold labels, runtime/model/GPU/service
  config, or production data.
- Do not change marketplace scoring, requirement extraction, mission matching,
  price-intelligence, scan scheduling, calibration, eBay sync, action-control
  launch/stop routes, or browser helper behavior.
- Do not broaden to router-wide Cockpit auth without a separate task card.
- Stop if the normal Marketplace browser path would require a broad API-key
  propagation redesign.

## Validation

- Task-card validate.
- Registry overlap check and claim.
- Ledger claimed and implementation state entries.
- RED focused backend tests before implementation.
- GREEN focused backend tests after implementation.
- Targeted Ruff check for touched Python files.
- `python3 -m py_compile` on touched Python files.
- `git diff --check`.
- Task-card `check-diff`, `check-report-artifacts`, and `check-closeout`.
