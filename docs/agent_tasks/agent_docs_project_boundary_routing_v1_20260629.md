---
job_id: agent_docs_project_boundary_routing_v1_20260629
lane: Reporting
supporting_lanes:
  - Repo Hygiene
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 1800
output_dir: reports/agent_jobs/agent_docs_project_boundary_routing_v1_20260629
mutation_mode: safe_extension
production_data_access: false
task_scope: control_plane_only
closeout_scope: docs_only
allowed_files:
  - AGENTS.md
  - docs/agent_tasks/agent_docs_project_boundary_routing_v1_20260629.md
  - reports/agent_jobs/agent_docs_project_boundary_routing_v1_20260629/STATE.md
  - reports/agent_jobs/agent_docs_project_boundary_routing_v1_20260629/VALIDATION.md
  - reports/agent_jobs/agent_docs_project_boundary_routing_v1_20260629/NEXT_GOAL.md
---

# Agent Docs Project Boundary Routing V1

## Objective

Update Tenn agent docs so project-boundary and external-sibling ownership
questions route directly from `AGENTS.md` to the active project-boundary guide.

## Evidence Inputs

- User request on 2026-06-29: "update agent docs".
- Canonical base:
  `ca424a2835094de40c366a36d4bb0bf04cd8246a`.
- Fresh worktree:
  `/home/l4nd0/tenn-agent-docs-project-boundary-routing-v1-20260629`.
- Branch:
  `control-plane/agent-docs-project-boundary-routing-v1-20260629`.
- Existing active project-boundary doc:
  `docs/dev_flow/PROJECT_BOUNDARIES.md`.
- Existing docs source map already routes to `PROJECT_BOUNDARIES.md`; this task
  only adds the missing `AGENTS.md` procedure-routing row.

## Scope

Allowed:

- Add this task card.
- Update `AGENTS.md` with a concise procedure-routing row for project ownership
  and external-sibling boundaries.
- Write report-local closeout files under this task `output_dir`.
- Run read-only guard, registry, ledger, grep, diff, and contract validation.
- Commit locally on this task branch.

Forbidden:

- Tenn product, runtime, backend, extraction, parser, prompt, evaluator,
  source-PDF, gold-label, DB, Qdrant, Redis, news, memory, service, model,
  Docker, dependency, CI, or runtime artifact changes.
- Greyhound repo file edits, DB changes, systemd unit edits, service starts,
  restarts, stops, runtime artifact edits, branch/worktree changes, cleanup, or
  GitHub writes.
- GitHub writes, branch push, merge, reset, stash, rebase, branch deletion,
  worktree deletion, pruning, parked-work changes, or unrelated cleanup.
- Editing unrelated dirty files in `/home/l4nd0/tenn`.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/agent_docs_project_boundary_routing_v1_20260629.md`
- `python3 scripts/tenn_dev_status.py`
- `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /home/l4nd0/tenn-agent-docs-project-boundary-routing-v1-20260629 --topic "agent docs project boundary routing update" --json`
- Focused grep proving `AGENTS.md` routes project-boundary work to
  `docs/dev_flow/PROJECT_BOUNDARIES.md`.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/agent_docs_project_boundary_routing_v1_20260629.md --no-write-report`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/agent_docs_project_boundary_routing_v1_20260629.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/agent_docs_project_boundary_routing_v1_20260629.md --repo-root .`
- Final `git status --short --untracked-files=all`

## Definition Of Done

- `AGENTS.md` remains concise and routes project-boundary decisions to
  `docs/dev_flow/PROJECT_BOUNDARIES.md`.
- No product/runtime/data/extraction or Greyhound-owned paths changed.
- Report-local validation records that runtime functionality was not proven
  because this task is docs-only.
