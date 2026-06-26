---
job_id: research_synthesis_route_guard_publish_pr_v1_20260626
lane: Query Orchestration
supporting_lanes:
  - Reporting
  - Runtime
  - Repo Hygiene
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/research_synthesis_route_guard_publish_pr_v1_20260626
mutation_mode: safe_extension
production_data_access: false
issue: 244
allowed_files:
  - docs/agent_tasks/research_synthesis_route_guard_publish_pr_v1_20260626.md
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
  - reports/agent_jobs/research_synthesis_route_guard_publish_pr_v1_20260626/README.md
  - reports/agent_jobs/research_synthesis_route_guard_publish_pr_v1_20260626/status.json
  - reports/agent_jobs/research_synthesis_route_guard_publish_pr_v1_20260626/PR_BODY.md
  - reports/agent_jobs/research_synthesis_route_guard_publish_pr_v1_20260626/REVIEW.md
  - reports/agent_jobs/research_synthesis_route_guard_publish_pr_v1_20260626/diff-check.json
github_writes_allowed:
  - push branch safe/issue244-research-synthesis-route-guard-v1-20260626 to origin
  - open one draft PR targeting migration/clean-runtime-baseline-reconstruct-v1
  - post one issue status comment on issue 244
forbidden_actions:
  - merge PR
  - close issue 244
  - change labels, milestones, projects, assignees, or issue title
  - mutate DB, Qdrant, Redis, news stores, memory, source PDFs, extraction prompts, gold labels, runtime state, model/GPU/service config, or production data
  - dependency install or dependency file edits
  - destructive git operations
---

# Research Synthesis Route Guard Publish PR

## Objective

Publish the already validated local issue #244 fix as a draft PR.

## Scope

- Re-run focused validation for the existing local route-guard fix.
- Commit the source, test, docs, task, and report artifacts already prepared for
  issue #244.
- Push branch `safe/issue244-research-synthesis-route-guard-v1-20260626`.
- Open one draft PR against `migration/clean-runtime-baseline-reconstruct-v1`.
- Post one issue #244 status comment with the draft PR link.

## Non-Goals

- Do not merge the PR.
- Do not close issue #244.
- Do not start backend/runtime services.
- Do not broaden research route behavior beyond the validated API-key guard.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/research_synthesis_route_guard_publish_pr_v1_20260626.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/research_synthesis_route_guard_publish_pr_v1_20260626.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/research_synthesis_route_guard_publish_pr_v1_20260626.md --repo-root .`
- `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_research_route_auth.py -q`
- `uv run --with ruff ruff check financial-engine_v2/backend/app/routes/research.py financial-engine_v2/backend/tests/test_research_route_auth.py`
- `python3 -m py_compile financial-engine_v2/backend/app/routes/research.py financial-engine_v2/backend/tests/test_research_route_auth.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/research_synthesis_route_guard_publish_pr_v1_20260626.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/research_synthesis_route_guard_publish_pr_v1_20260626.md --repo-root .`

## Done Criteria

- Draft PR exists for issue #244.
- Issue #244 has a status comment linking the draft PR.
- Registry claim is released.
- Ledger has a `pr_opened` entry.
- Issue remains open until canonical acceptance.
