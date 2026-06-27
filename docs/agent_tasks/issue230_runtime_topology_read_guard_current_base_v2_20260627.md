---
job_id: issue230_runtime_topology_read_guard_current_base_v2_20260627
title: Replace stale Cockpit runtime topology read guard PR on current base
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
output_dir: reports/agent_jobs/issue230_runtime_topology_read_guard_current_base_v2_20260627
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
related_issue: 230
allowed_files:
  - docs/agent_tasks/issue230_runtime_topology_read_guard_current_base_v2_20260627.md
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
  - reports/agent_jobs/issue230_runtime_topology_read_guard_current_base_v2_20260627/README.md
  - reports/agent_jobs/issue230_runtime_topology_read_guard_current_base_v2_20260627/status.json
  - reports/agent_jobs/issue230_runtime_topology_read_guard_current_base_v2_20260627/VALIDATION.md
  - reports/agent_jobs/issue230_runtime_topology_read_guard_current_base_v2_20260627/REVIEW.md
  - reports/agent_jobs/issue230_runtime_topology_read_guard_current_base_v2_20260627/diff-check.json
docs_impact: DOCS_REQUIRED
docs_checked:
  - AGENTS.md
  - docs/README.md
  - docs/dev_flow/REPO_PATH_OWNERSHIP_AND_WORK_PRESERVATION.md
  - docs/architecture/19_backend_api_surface.md
docs_changed:
  - docs/architecture/19_backend_api_surface.md
docs_followup: NONE
reason: "Issue #230 reports unguarded Cockpit runtime topology read routes exposing model, runtime config, and queue state; PR #440 is stale/conflicting."
task_tier: medium
recommended_model: "standard coding model"
actual_model: "Codex GPT-5"
why_this_model: "The change is a focused current-base replay of an already reviewed backend route guard plus narrow client header continuity."
worker_model_allowed: false
worker_decision_limit: "main orchestrator only; no subagent needed for this narrow current-base replacement."
escalation_needed: false
---

# Issue #230 Runtime Topology Read Guard V2

## Objective

Fix issue #230 on current canonical base by replacing stale/conflicting PR #440.
Require the existing local API-key dependency on Cockpit runtime topology read
routes whenever `settings.local_api_key` is configured, while preserving no-key
local-dev behavior and authenticated Cockpit UI diagnostics.

## Duplicate-Work Classification

- Classification: `SUPERSEDE_STALE_PR_WITH_CURRENT_BASE_REPLACEMENT`
- Stale work preserved: PR #440,
  `safe/issue230-runtime-topology-read-guard-current-base-v1-20260627`,
  commit `acc41dedc50c121dfa88947cf92c1ab7a3e22af7`.
- Reason: PR #440 has historical green checks but is now `DIRTY` /
  `CONFLICTING` against canonical `aa177c7c22f2651c64b5ddbab755333462cea2f8`.

## Scope

Allowed:

- Replay the #440 source/test/doc intent onto current canonical base.
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
- Write closeout evidence under the v2 report directory.
- Open a replacement PR, comment on PR #440 that it is superseded, request
  Codex review, merge after green checks and clear review, and close #230 with
  `DONE_WITH_RISK` / `PARTIAL` runtime-proof wording.

Forbidden:

- No production DB, Qdrant, Redis, news, memory-store, source-document,
  canonical financial truth, parser routing, prompts, gold labels, runtime,
  model, GPU, service config, dependency, lockfile, CI, host-global, or
  production data mutation.
- No model-load behavior changes tracked by adjacent route issues.
- No telemetry route changes tracked by #218/#223.
- No chat/session route-guard behavior, action-control, preference,
  holdings/watchlist, Strategy Lab, or marketplace route-guard work.
- No merge, rebase, reset, stash, clean, branch deletion, force-push, or parked
  work mutation.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue230_runtime_topology_read_guard_current_base_v2_20260627.md`
- `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_cockpit_api_models.py -q`
- `uv run --with ruff ruff check financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_cockpit_api_models.py`
- `python3 -m py_compile financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_cockpit_api_models.py`
- `cd cockpit-ui && npm test -- --run lib/api-client.test.ts`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/issue230_runtime_topology_read_guard_current_base_v2_20260627.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/issue230_runtime_topology_read_guard_current_base_v2_20260627.md --repo-root .`
- `python3 scripts/agent_task_ledger.py --repo-root . validate`

## Done Criteria

- The three backend runtime-topology read routes register `require_api_key`.
- Configured API-key mode rejects missing/wrong keys before runtime/model/queue
  probing.
- Matching configured keys allow representative config/model/queue reads.
- No-key local-dev mode preserves existing read behavior.
- The Cockpit API client sends `X-API-Key` for guarded read helpers when
  `NEXT_PUBLIC_API_KEY` or stored browser key is configured.
- Diff remains inside `allowed_files`.
- Replacement PR is opened and merged only after green GitHub checks and clear
  review; issue #230 is closed only after merge containment and evidence
  comment.
