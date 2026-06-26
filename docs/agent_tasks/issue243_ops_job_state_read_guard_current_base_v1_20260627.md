---
job_id: issue243_ops_job_state_read_guard_current_base_v1_20260627
title: Gate Ops job-state reads and stream before exposing run artifacts
lane: Reporting
supporting_lanes:
  - Evaluation
  - Repo Hygiene
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/issue243_ops_job_state_read_guard_current_base_v1_20260627
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
related_issue: 243
allowed_files:
  - docs/agent_tasks/issue243_ops_job_state_read_guard_current_base_v1_20260627.md
  - docs/architecture/19_backend_api_surface.md
  - financial-engine_v2/backend/app/routes/ops_api.py
  - financial-engine_v2/backend/tests/test_ops_api.py
  - cockpit-ui/lib/ops-api-client.ts
  - cockpit-ui/lib/ops-api-client.test.ts
  - cockpit-ui/hooks/use-job-stream.ts
  - reports/agent_jobs/issue243_ops_job_state_read_guard_current_base_v1_20260627/README.md
  - reports/agent_jobs/issue243_ops_job_state_read_guard_current_base_v1_20260627/status.json
  - reports/agent_jobs/issue243_ops_job_state_read_guard_current_base_v1_20260627/VALIDATION.md
  - reports/agent_jobs/issue243_ops_job_state_read_guard_current_base_v1_20260627/REVIEW.md
  - reports/agent_jobs/issue243_ops_job_state_read_guard_current_base_v1_20260627/diff-check.json
docs_impact: DOCS_REQUIRED
docs_checked:
  - AGENTS.md
  - docs/README.md
  - docs/architecture/19_backend_api_surface.md
docs_changed:
  - docs/architecture/19_backend_api_surface.md
docs_followup: NONE
reason: "Issue #243 reports unguarded Ops job-state read and stream endpoints that expose run metadata/artifact paths when local API auth is configured."
task_tier: medium
recommended_model: "standard coding model"
actual_model: "Codex GPT-5"
why_this_model: "The change is a focused backend route guard plus narrow Cockpit client/header tests."
worker_model_allowed: false
worker_decision_limit: "main orchestrator only; no subagent needed for this narrow security guard slice."
escalation_needed: false
---

# Issue #243 Ops Job-State Read Guard

## Objective

Fix issue #243 on current canonical base by requiring the local API-key guard on
Ops job-state reads and the Ops SSE stream whenever `settings.local_api_key` is
configured, while keeping unauthenticated local-dev behavior unchanged when no
key is configured.

## Duplicate-Work Classification

- Old local worktree:
  `/home/l4nd0/tenn-issue243-ops-job-state-read-guard-v1-20260626`
- Old branch:
  `safe/issue243-ops-job-state-read-guard-v1-20260626`
- Classification: `ADOPT/PRESERVE`
- Reason: useful validated local work exists in a dirty unpublished checkout,
  but current canonical base still has unguarded Ops read/stream routes and no
  current-base PR was found for issue #243.

## Scope

Allowed:

- Add `require_api_key` dependencies to these backend read routes:
  - `GET /api/ops/jobs`
  - `GET /api/ops/jobs/active`
  - `GET /api/ops/jobs/{job_id}`
  - `GET /api/ops/jobs/{job_id}/events`
  - `GET /api/ops/jobs/{job_id}/artifacts`
  - `GET /api/ops/stream`
- Add focused backend tests proving the read routes register the API-key
  dependency and reject missing/wrong keys when a key is configured.
- Update the Cockpit Ops client so job-state reads pass `X-API-Key` from
  `NEXT_PUBLIC_API_KEY` when configured.
- Replace native browser `EventSource` for Ops streaming with an explicit
  header-capable SSE client so durable API keys are not placed in URLs.
- Add focused frontend tests for Ops read headers and stream header construction.
- Document the `/api/ops/*` auth contract in the backend API surface doc.
- Write closeout evidence under the report directory.

Forbidden:

- No DB, Qdrant, Redis, news, memory-store, extraction, source-document,
  canonical financial truth, parser routing, prompts, gold labels, runtime,
  model, GPU, service config, dependency, lockfile, CI, host-global, or
  production data mutation.
- No broad Cockpit UI redesign, route-wide auth refactor, app-wide fetch helper
  rewrite, or unrelated cleanup.
- No merge, rebase, reset, stash, clean, branch deletion, force-push, or issue
  close without explicit approval.

## Required Validation

- RED backend route-dependency test before source implementation.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue243_ops_job_state_read_guard_current_base_v1_20260627.md`
- `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_ops_api.py -q`
- `pnpm --dir cockpit-ui exec vitest run lib/ops-api-client.test.ts`
- `pnpm --dir cockpit-ui exec eslint lib/ops-api-client.ts lib/ops-api-client.test.ts hooks/use-job-stream.ts`
- `uv run --with ruff ruff check financial-engine_v2/backend/app/routes/ops_api.py financial-engine_v2/backend/tests/test_ops_api.py`
- `python3 -m py_compile financial-engine_v2/backend/app/routes/ops_api.py financial-engine_v2/backend/tests/test_ops_api.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/issue243_ops_job_state_read_guard_current_base_v1_20260627.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/issue243_ops_job_state_read_guard_current_base_v1_20260627.md --repo-root .`

## Done Criteria

- The six Ops read/stream routes register `require_api_key`.
- Configured API-key mode rejects missing/wrong keys on representative Ops
  reads before any tracker data is returned.
- Cockpit Ops reads send `X-API-Key` when `NEXT_PUBLIC_API_KEY` is configured.
- Ops streaming uses a header-capable SSE client with `start: false` and no API
  key in the URL.
- Diff remains inside `allowed_files`.
- PR is opened; issue #243 is not closed unless explicitly approved.
