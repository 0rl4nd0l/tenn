---
job_id: issue230_runtime_topology_read_guard_current_base_v1_20260627
title: Gate Cockpit runtime topology read routes before exposing config, models, and queue state
lane: Reporting
supporting_lanes:
  - Runtime
  - Query Orchestration
  - Repo Hygiene
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/issue230_runtime_topology_read_guard_current_base_v1_20260627
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
related_issue: 230
allowed_files:
  - docs/agent_tasks/issue230_runtime_topology_read_guard_current_base_v1_20260627.md
  - docs/architecture/19_backend_api_surface.md
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/tests/test_cockpit_api_models.py
  - cockpit-ui/lib/api-client.ts
  - cockpit-ui/lib/api-client.test.ts
  - cockpit-ui/components/cockpit/cockpit-sidebar.tsx
  - cockpit-ui/components/cockpit/cockpit-status-bar.tsx
  - cockpit-ui/components/cockpit/settings/settings-screen.tsx
  - cockpit-ui/components/cockpit/chat/chat-screen.tsx
  - cockpit-ui/components/cockpit/verification/verification-screen.tsx
  - cockpit-ui/components/cockpit/operations/gpu-workload-card.tsx
  - reports/agent_jobs/issue230_runtime_topology_read_guard_current_base_v1_20260627/README.md
  - reports/agent_jobs/issue230_runtime_topology_read_guard_current_base_v1_20260627/status.json
  - reports/agent_jobs/issue230_runtime_topology_read_guard_current_base_v1_20260627/VALIDATION.md
  - reports/agent_jobs/issue230_runtime_topology_read_guard_current_base_v1_20260627/REVIEW.md
  - reports/agent_jobs/issue230_runtime_topology_read_guard_current_base_v1_20260627/diff-check.json
docs_impact: DOCS_REQUIRED
docs_checked:
  - AGENTS.md
  - docs/README.md
  - docs/dev_flow/REPO_PATH_OWNERSHIP_AND_WORK_PRESERVATION.md
  - docs/architecture/19_backend_api_surface.md
docs_changed:
  - docs/architecture/19_backend_api_surface.md
docs_followup: NONE
reason: "Issue #230 reports unguarded Cockpit runtime topology read routes exposing model, runtime config, and queue state."
task_tier: medium
recommended_model: "standard coding model"
actual_model: "Codex GPT-5"
why_this_model: "The change is a focused backend route guard plus narrow client header continuity tests."
worker_model_allowed: false
worker_decision_limit: "main orchestrator only; no subagent needed for this narrow route guard."
escalation_needed: false
---

# Issue #230 Runtime Topology Read Guard

## Objective

Fix issue #230 on current canonical base by requiring the existing local
API-key dependency on Cockpit runtime topology read routes whenever
`settings.local_api_key` is configured, while preserving no-key local-dev
behavior and authenticated Cockpit UI diagnostics.

## Duplicate-Work Classification

- Classification: `NO_MATCHING_ACTIVE_WORK_FOUND`
- Reason: no open/current PR, task card, or active registry entry was found for
  issue #230; canonical still has unguarded `/config`, `/models`, and `/queue`
  route decorators.

## Scope

Allowed:

- Add `require_api_key` dependencies to these backend read routes:
  - `GET /api/cockpit/config`
  - `GET /api/cockpit/models`
  - `GET /api/cockpit/queue`
- Add focused backend route-auth tests proving missing/wrong configured keys are
  denied before runtime/model/queue probing and matching/no-key behavior is
  preserved.
- Add focused API-client tests proving the configured browser API key is sent
  for config, model inventory, and queue reads.
- Add `X-API-Key` continuity to direct Cockpit browser config fetches that
  cannot go through `apiFetch`.
- Document the runtime-topology read auth contract in the backend API surface
  doc.
- Write closeout evidence under the report directory.

Forbidden:

- No production DB, Qdrant, Redis, news, memory-store, source-document,
  canonical financial truth, parser routing, prompts, gold labels, runtime,
  model, GPU, service config, dependency, lockfile, CI, host-global, or
  production data mutation.
- No model-load behavior changes tracked by adjacent route issues.
- No telemetry route changes tracked by #218/#223.
- No chat/session route-guard behavior, action-control, preference,
  holdings/watchlist, Strategy Lab, or marketplace route-guard work.
- No merge, rebase, reset, stash, clean, branch deletion, force-push, or issue
  close without explicit approval.

## Required Validation

- RED backend route-auth test before source implementation.
- RED API-client header-continuity test before client implementation.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue230_runtime_topology_read_guard_current_base_v1_20260627.md`
- `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_cockpit_api_models.py -q`
- `uv run --with ruff ruff check financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_cockpit_api_models.py`
- `python3 -m py_compile financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_cockpit_api_models.py`
- `cd cockpit-ui && npm test -- --run lib/api-client.test.ts`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/issue230_runtime_topology_read_guard_current_base_v1_20260627.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/issue230_runtime_topology_read_guard_current_base_v1_20260627.md --repo-root .`

## Done Criteria

- The three backend runtime-topology read routes register `require_api_key`.
- Configured API-key mode rejects missing/wrong keys before runtime/model/queue
  probing.
- Matching configured keys allow representative config/model/queue reads.
- No-key local-dev mode preserves existing read behavior.
- The Cockpit API client sends `X-API-Key` for the guarded read helpers when
  `NEXT_PUBLIC_API_KEY` is configured.
- Diff remains inside `allowed_files`.
- PR is opened; issue #230 is not closed unless explicitly approved.
