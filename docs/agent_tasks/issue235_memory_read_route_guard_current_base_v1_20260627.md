---
job_id: issue235_memory_read_route_guard_current_base_v1_20260627
title: Gate backend memory read routes before exposing thesis and qualitative memory
lane: Memory
supporting_lanes:
  - Provenance
  - Reporting
  - Repo Hygiene
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/issue235_memory_read_route_guard_current_base_v1_20260627
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
related_issue: 235
allowed_files:
  - docs/agent_tasks/issue235_memory_read_route_guard_current_base_v1_20260627.md
  - docs/architecture/19_backend_api_surface.md
  - financial-engine_v2/backend/app/api/context.py
  - financial-engine_v2/backend/tests/test_memory_read_route_auth.py
  - reports/agent_jobs/issue235_memory_read_route_guard_current_base_v1_20260627/README.md
  - reports/agent_jobs/issue235_memory_read_route_guard_current_base_v1_20260627/status.json
  - reports/agent_jobs/issue235_memory_read_route_guard_current_base_v1_20260627/VALIDATION.md
  - reports/agent_jobs/issue235_memory_read_route_guard_current_base_v1_20260627/REVIEW.md
  - reports/agent_jobs/issue235_memory_read_route_guard_current_base_v1_20260627/diff-check.json
docs_impact: DOCS_REQUIRED
docs_checked:
  - AGENTS.md
  - docs/README.md
  - docs/architecture/22_memory_ownership_map.md
  - docs/architecture/21_cockpit_client_contract.md
  - docs/architecture/19_backend_api_surface.md
docs_changed:
  - docs/architecture/19_backend_api_surface.md
docs_followup: NONE
reason: "Issue #235 reports unguarded backend memory read routes exposing durable qualitative memory and user thesis state."
task_tier: medium
recommended_model: "standard coding model"
actual_model: "Codex GPT-5"
why_this_model: "The change is a focused backend route guard plus narrow route-auth tests."
worker_model_allowed: false
worker_decision_limit: "main orchestrator only; no subagent needed for this narrow memory read-route guard."
escalation_needed: false
---

# Issue #235 Memory Read Route Guard

## Objective

Fix issue #235 on current canonical base by requiring the existing local
API-key dependency on backend memory read routes whenever `settings.local_api_key`
is configured, while preserving no-key local-dev behavior.

## Duplicate-Work Classification

- Classification: `NO_MATCHING_ACTIVE_WORK_FOUND`
- Reason: no open/current PR or ledger entry was found for issue #235; canonical
  still has unguarded memory read route decorators.

## Scope

Allowed:

- Add `require_api_key` dependencies to these backend read routes:
  - `GET /api/context/memory`
  - `GET /api/context/memory/index`
  - `GET /api/context/thesis`
  - `GET /api/context/company_dump`
- Add focused backend route-auth tests proving missing/wrong configured keys are
  denied before memory services/database work and matching/no-key behavior is
  preserved.
- Document the backend memory-read auth contract in the backend API surface doc.
- Write closeout evidence under the report directory.

Verified but not changed:

- Cockpit BFF memory read routes already use `copyRequestHeaders(request)`.
- Memory Workbench browser reads already include `X-API-Key` when an `apiKey`
  prop is configured.

Forbidden:

- No production DB, Qdrant, Redis, news, memory-store, source-document,
  canonical financial truth, parser routing, prompts, gold labels, runtime,
  model, GPU, service config, dependency, lockfile, CI, host-global, or
  production data mutation.
- No weakening memory write confirmation gates or user-thesis proposal flows.
- No frontend memory store, BFF authority expansion, broad Cockpit UI redesign,
  app-wide fetch helper rewrite, or unrelated route guard work.
- No merge, rebase, reset, stash, clean, branch deletion, force-push, or issue
  close without explicit approval.

## Required Validation

- RED backend route-auth test before source implementation.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue235_memory_read_route_guard_current_base_v1_20260627.md`
- `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_memory_read_route_auth.py -q`
- `uv run --with ruff ruff check financial-engine_v2/backend/app/api/context.py financial-engine_v2/backend/tests/test_memory_read_route_auth.py`
- `python3 -m py_compile financial-engine_v2/backend/app/api/context.py financial-engine_v2/backend/tests/test_memory_read_route_auth.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/issue235_memory_read_route_guard_current_base_v1_20260627.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/issue235_memory_read_route_guard_current_base_v1_20260627.md --repo-root .`

## Done Criteria

- The four backend memory read routes register `require_api_key`.
- Configured API-key mode rejects missing/wrong keys before durable memory
  payloads are loaded.
- Matching configured keys allow representative memory reads.
- No-key local-dev mode preserves existing read behavior.
- Diff remains inside `allowed_files`.
- PR is opened; issue #235 is not closed unless explicitly approved.
