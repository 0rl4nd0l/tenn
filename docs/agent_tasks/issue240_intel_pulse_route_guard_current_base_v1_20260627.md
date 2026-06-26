---
job_id: issue240_intel_pulse_route_guard_current_base_v1_20260627
lane: Reporting
supporting_lanes:
  - Evaluation
  - Financial Truth
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/issue240_intel_pulse_route_guard_current_base_v1_20260627.md
  - docs/architecture/19_backend_api_surface.md
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/tests/test_local_api_key.py
  - financial-engine_v2/backend/tests/test_cockpit_intel_pulse_route_auth.py
  - cockpit-ui/lib/api-client.ts
  - cockpit-ui/lib/api-client.test.ts
  - reports/agent_jobs/issue240_intel_pulse_route_guard_current_base_v1_20260627/README.md
  - reports/agent_jobs/issue240_intel_pulse_route_guard_current_base_v1_20260627/status.json
  - reports/agent_jobs/issue240_intel_pulse_route_guard_current_base_v1_20260627/VALIDATION.md
  - reports/agent_jobs/issue240_intel_pulse_route_guard_current_base_v1_20260627/REVIEW.md
  - reports/agent_jobs/issue240_intel_pulse_route_guard_current_base_v1_20260627/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/issue240_intel_pulse_route_guard_current_base_v1_20260627
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
docs_impact: DOCS_REQUIRED
docs_checked:
  - AGENTS.md
  - docs/README.md
  - docs/dev_flow/REPO_PATH_OWNERSHIP_AND_WORK_PRESERVATION.md
  - docs/architecture/19_backend_api_surface.md
  - "issue #240"
docs_changed:
  - docs/architecture/19_backend_api_surface.md
docs_followup: NONE
task_tier: medium
recommended_model: "standard coding model"
actual_model: "Codex GPT-5"
why_this_model: "Small backend/frontend route-auth repair with existing local evidence, current-base adoption, focused tests, review, and PR handling."
worker_model_allowed: false
worker_decision_limit: "No workers used; prior local patch and affected route/client files are narrow enough to inspect directly."
escalation_needed: false
related_issue: 240
supersedes:
  - cockpit_intel_pulse_route_guard_v1_20260626
---

# Issue 240 Intel Pulse Route Guard Current Base

## Objective

Adopt the previously prepared local issue #240 fix onto current canonical:
require the configured local API key for `GET /api/cockpit/pulse` and
`GET /api/cockpit/matrix`, and send that API key from the Intel Ops client
calls.

## Existing Work Classification

- `ADOPT`: `/home/l4nd0/tenn-issue240-intel-pulse-route-guard-v1-20260626`
  contains a focused local fix, tests, and report evidence.
- `PRESERVE`: leave that older worktree untouched because it is dirty,
  unpublished, and based on older canonical `857e76c3`.
- `NO_FOLLOWUP`: no new issue is needed if focused validation passes and a PR
  is opened for #240.

## Scope

- Add `require_api_key` to the Intel Pulse and diagnostic Matrix routes.
- Add backend tests proving configured-key mode rejects missing keys before
  service access and accepts matching keys for both routes.
- Add Pulse/Matrix entries to the shared protected-route dependency test.
- Update `getIntelPulse()` and `getDiagnosticMatrix()` to send `X-API-Key`.
- Add focused API-client tests for Pulse/Matrix header propagation.
- Document the guarded Intel Pulse and Matrix route contract.
- Write report artifacts and open a PR if gates pass.

## Hard Stops

- Do not change financial truth, extraction scoring semantics, diagnostic
  matrix cell logic, Signals/Memory capability decisions, ingestion,
  extraction outputs, parser prompts, source PDFs, gold labels, DB, Qdrant,
  Redis, news stores, memory, model/GPU config, services, or production data.
- Do not start runtime services or run live Cockpit/browser smoke tests.
- Do not install project dependencies or mutate lockfiles/package manifests.
- Do not broaden into runtime-topology guards tracked by #230 or
  Signals/Memory wiring tracked by #148.
- Do not merge, rebase, reset, stash, clean, prune, or delete any branches or
  worktrees.

## Validation

- Task-card validate.
- Registry overlap check and claim.
- Ledger claimed and PR-open entries.
- RED backend focused pytest before source implementation.
- GREEN backend focused pytest:
  `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt pytest -q financial-engine_v2/backend/tests/test_local_api_key.py financial-engine_v2/backend/tests/test_cockpit_intel_pulse_route_auth.py`
- Frontend focused Vitest for `cockpit-ui/lib/api-client.test.ts`, or record
  the exact dependency/tooling blocker without installing dependencies.
- Ruff touched Python files:
  `uv run --with ruff ruff check financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_local_api_key.py financial-engine_v2/backend/tests/test_cockpit_intel_pulse_route_auth.py`
- Py compile touched Python files:
  `python3 -m py_compile financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_local_api_key.py financial-engine_v2/backend/tests/test_cockpit_intel_pulse_route_auth.py`
- `git diff --check`.
- Code-reviewer pass.
- Task-card `check-diff`.
- Task-card `check-report-artifacts`.
- Ledger validate.
