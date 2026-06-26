---
job_id: issue242_context_diagnostics_guard_current_base_v1_20260627
title: Guard or redact context diagnostics before exposing extraction failures
lane: Evaluation
supporting_lanes:
  - Provenance
  - Reporting
  - Financial Truth
  - Repo Hygiene
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/issue242_context_diagnostics_guard_current_base_v1_20260627
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
related_issue: 242
allowed_files:
  - docs/agent_tasks/issue242_context_diagnostics_guard_current_base_v1_20260627.md
  - docs/architecture/19_backend_api_surface.md
  - financial-engine_v2/backend/app/api/context.py
  - financial-engine_v2/backend/tests/test_context_diagnostics_route_auth.py
  - cockpit-ui/lib/api-client.ts
  - cockpit-ui/lib/api-client.test.ts
  - cockpit-ui/components/cockpit/verification/verification-screen.tsx
  - reports/agent_jobs/issue242_context_diagnostics_guard_current_base_v1_20260627/README.md
  - reports/agent_jobs/issue242_context_diagnostics_guard_current_base_v1_20260627/status.json
  - reports/agent_jobs/issue242_context_diagnostics_guard_current_base_v1_20260627/VALIDATION.md
  - reports/agent_jobs/issue242_context_diagnostics_guard_current_base_v1_20260627/REVIEW.md
  - reports/agent_jobs/issue242_context_diagnostics_guard_current_base_v1_20260627/diff-check.json
docs_impact: DOCS_REQUIRED
docs_checked:
  - AGENTS.md
  - docs/README.md
  - docs/architecture/SYSTEM_CONTRACT.md
  - docs/architecture/19_backend_api_surface.md
docs_changed:
  - docs/architecture/19_backend_api_surface.md
docs_followup: NONE
reason: "Issue #242 reports unauthenticated context diagnostics exposing source paths, hashes, extraction failures, low-confidence rows, and verification run history."
task_tier: medium
recommended_model: "standard coding model"
actual_model: "Codex GPT-5"
why_this_model: "The change is a focused backend diagnostic redaction/route guard plus narrow Cockpit client/header tests."
worker_model_allowed: false
worker_decision_limit: "main orchestrator only; useful prior local work exists and the replay is narrow."
escalation_needed: false
---

# Issue #242 Context Diagnostics Guard

## Objective

Fix issue #242 on current canonical base by separating ordinary
backend-authoritative context reads from operator/evaluation diagnostics.
Keep `GET /api/context/ticker` usable for normal Cockpit context reads, but
redact diagnostic/path fields from unauthenticated configured-key requests.
Require the local API key for `GET /api/context/verification` and
`GET /api/context/verification/runs` when `settings.local_api_key` is
configured, while preserving no-key local-dev behavior.

## Duplicate-Work Classification

- Old local worktree:
  `/home/l4nd0/tenn-issue242-context-diagnostics-guard-v1-20260626`
- Old branch:
  `safe/issue242-context-diagnostics-guard-v1-20260626`
- Classification: `ADOPT/PRESERVE`
- Reason: useful validated local work exists in a dirty unpublished checkout,
  but current canonical base still exposes the #242 diagnostics and no
  current-base PR was found for issue #242.

## Scope

Allowed:

- Add a configured-key redaction path for unauthenticated
  `GET /api/context/ticker` so normal context fields remain available while
  diagnostic/source-path fields are withheld.
- Preserve the full ticker diagnostic payload for authenticated requests and
  for no-key local-dev mode.
- Guard `GET /api/context/verification` and
  `GET /api/context/verification/runs` with the existing `require_api_key`
  dependency.
- Update Cockpit API-client and verification screen calls so guarded
  diagnostics send `X-API-Key` when configured.
- Add focused backend tests for configured-key redaction/guards,
  authenticated success, and no-key local-dev behavior.
- Add focused frontend API-client tests for header propagation.
- Document the selected auth/redaction contract in the backend API surface doc.
- Write closeout evidence under the report directory.

Forbidden:

- No DB, Qdrant, Redis, news, memory-store, extraction scoring, source
  documents, canonical financial truth, parser routing, prompts, gold labels,
  runtime, model, GPU, service config, dependency, lockfile, CI, host-global,
  or production data mutation.
- No replacement of backend context authority with client-side financial reads
  or local Cockpit stores.
- No broad Cockpit UI redesign, app-wide fetch helper rewrite, memory route
  guards (#235), extraction review reads (#241), document history (#239),
  Intel Pulse (#240), or claim verification (#224).
- No merge, rebase, reset, stash, clean, branch deletion, force-push, or issue
  close without explicit approval.

## Required Validation

- RED backend focused pytest before source implementation.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue242_context_diagnostics_guard_current_base_v1_20260627.md`
- `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_context_diagnostics_route_auth.py -q`
- `pnpm --dir cockpit-ui exec vitest run lib/api-client.test.ts`
- `pnpm --dir cockpit-ui exec eslint lib/api-client.ts lib/api-client.test.ts components/cockpit/verification/verification-screen.tsx`
- `uv run --with ruff ruff check financial-engine_v2/backend/app/api/context.py financial-engine_v2/backend/tests/test_context_diagnostics_route_auth.py`
- `python3 -m py_compile financial-engine_v2/backend/app/api/context.py financial-engine_v2/backend/tests/test_context_diagnostics_route_auth.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/issue242_context_diagnostics_guard_current_base_v1_20260627.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/issue242_context_diagnostics_guard_current_base_v1_20260627.md --repo-root .`

## Done Criteria

- Unauthenticated `GET /api/context/ticker` under configured-key mode returns
  ordinary context without diagnostic/path fields.
- Authenticated `GET /api/context/ticker` preserves the existing full payload.
- No-key local-dev mode preserves the existing full payload.
- `GET /api/context/verification` and
  `GET /api/context/verification/runs` deny missing/wrong configured keys and
  accept matching keys.
- Cockpit verification client paths send `X-API-Key` when configured.
- Diff remains inside `allowed_files`.
- PR is opened; issue #242 is not closed unless explicitly approved.
