---
job_id: research_synthesis_route_guard_v1_20260626
title: Gate research synthesis route before server-side LLM inference
lane: Query Orchestration
supporting_lanes:
  - Reporting
  - Runtime
  - Repo Hygiene
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/research_synthesis_route_guard_v1_20260626
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: issue_comment_only
related_issue: 244
allowed_files:
  - docs/agent_tasks/research_synthesis_route_guard_v1_20260626.md
  - docs/architecture/19_backend_api_surface.md
  - financial-engine_v2/backend/app/routes/research.py
  - financial-engine_v2/backend/tests/test_research_route_auth.py
  - reports/agent_jobs/research_synthesis_route_guard_v1_20260626/README.md
  - reports/agent_jobs/research_synthesis_route_guard_v1_20260626/status.json
  - reports/agent_jobs/research_synthesis_route_guard_v1_20260626/validation.json
  - reports/agent_jobs/research_synthesis_route_guard_v1_20260626/diff-check.json
  - reports/agent_jobs/research_synthesis_route_guard_v1_20260626/CODE_REVIEW.json
  - reports/agent_jobs/research_synthesis_route_guard_v1_20260626/NEXT_GOAL.md
  - reports/agent_jobs/research_synthesis_route_guard_v1_20260626/issue_comment.md
  - reports/agent_jobs/research_synthesis_route_guard_v1_20260626/guard_preflight.json
  - reports/agent_jobs/research_synthesis_route_guard_v1_20260626/registry_active_jobs_initial.json
  - reports/agent_jobs/research_synthesis_route_guard_v1_20260626/registry_active_jobs_final.json
docs_impact: DOCS_REQUIRED
docs_checked:
  - AGENTS.md
  - docs/README.md
  - docs/architecture/19_backend_api_surface.md
docs_changed:
  - docs/architecture/19_backend_api_surface.md
docs_followup: NONE
reason: "Issue #244 reports that POST /research/synthesize reaches server-side synthesis without the local API-key dependency."
task_tier: medium
recommended_model: "standard coding model"
actual_model: "Codex GPT-5"
why_this_model: "The change is a single backend route guard with focused route-auth tests."
worker_model_allowed: false
worker_decision_limit: "main orchestrator only; no subagent needed for this single-route guard."
escalation_needed: false
---

# Research Synthesis Route Guard

## Objective

Fix issue #244 by requiring the local API-key guard on
`POST /research/synthesize` whenever `settings.local_api_key` is configured.
Preserve unauthenticated local-dev behavior when no key is configured.

## Scope

Allowed:

- Add `require_api_key` to `POST /research/synthesize`.
- Add focused backend tests proving:
  - the route registers the API-key dependency,
  - missing/wrong keys fail before `synthesize_research()` is called,
  - matching keys allow the route and call synthesis.
- Document the route authentication contract in the backend API surface doc.
- Write closeout evidence under the report directory.

Forbidden:

- No DB, Qdrant, Redis, news, memory-store, extraction, source-document,
  canonical financial truth, parser routing, prompts, gold labels, runtime,
  model, GPU, service config, dependency, lockfile, CI, host-global, or
  production data mutation.
- No moving research synthesis into Cockpit, adding client-side synthesis
  authority, broad route refactor, or unrelated cleanup.
- No merge, rebase, reset, stash, clean, branch deletion, force-push, or issue
  close without explicit approval.

## Required Preflight

1. Run `tenn-git-guard` preflight from the selected worktree.
2. Validate this task card.
3. Check registry active jobs and overlap.
4. Claim the task card in the registry.
5. Validate the task ledger.
6. Confirm no active overlapping PR/branch/worktree for issue #244.

## Required Validation

- RED backend route-auth test before source implementation.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/research_synthesis_route_guard_v1_20260626.md`
- `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_research_route_auth.py -q`
- `uv run --with ruff ruff check financial-engine_v2/backend/app/routes/research.py financial-engine_v2/backend/tests/test_research_route_auth.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/research_synthesis_route_guard_v1_20260626.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/research_synthesis_route_guard_v1_20260626.md`

## Done Criteria

- `POST /research/synthesize` registers `require_api_key`.
- Configured API-key mode rejects missing/wrong keys before server-side
  synthesis runs.
- Matching keys still allow synthesis.
- Diff remains inside `allowed_files`.
- Issue #244 receives a closeout comment with validation status and remaining
  risks; the issue is not closed unless explicitly approved.
