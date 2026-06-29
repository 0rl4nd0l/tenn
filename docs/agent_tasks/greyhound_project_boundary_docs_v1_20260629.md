---
job_id: greyhound_project_boundary_docs_v1_20260629
lane: Reporting
supporting_lanes:
  - Repo Hygiene
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 1800
output_dir: reports/agent_jobs/greyhound_project_boundary_docs_v1_20260629
mutation_mode: safe_extension
production_data_access: false
task_scope: control_plane_only
closeout_scope: docs_only
allowed_files:
  - docs/agent_tasks/greyhound_project_boundary_docs_v1_20260629.md
  - docs/dev_flow/PROJECT_BOUNDARIES.md
  - docs/README.md
  - reports/agent_jobs/greyhound_project_boundary_docs_v1_20260629/STATE.md
  - reports/agent_jobs/greyhound_project_boundary_docs_v1_20260629/DECISIONS.md
  - reports/agent_jobs/greyhound_project_boundary_docs_v1_20260629/VALIDATION.md
  - reports/agent_jobs/greyhound_project_boundary_docs_v1_20260629/NEXT_GOAL.md
---

# Greyhound Project Boundary Docs V1

## Objective

Codify the Tenn / Greyhound boundary as a Tenn docs/control-plane operating
rule: Greyhound is an external sibling project, not a Tenn subsystem.

## Evidence Inputs

- User request from 2026-06-29 requiring `tenn-fix`, a fresh canonical Tenn
  control-plane worktree, a docs-only task card, no Tenn product/runtime/
  extraction code changes, no Greyhound repo/runtime/service/GitHub mutation,
  and focused validation.
- Review board:
  `/home/l4nd0/tenn/reports/agent_jobs/tenn_greyhound_repo_separation_review_board_20260629T175721+1000/`
- Fresh worktree:
  `/home/l4nd0/tenn-greyhound-project-boundary-docs-v1-20260629`
- Branch: `docs/greyhound-project-boundary-v1-20260629`
- Initial task base HEAD: `3b32b8b3be8b04bb5a198c71ec928db182438f17`
- Publish refresh canonical parent:
  `6c486d07743d3483d05fa163dc5c02fd66b68863`

## Scope

Allowed:

- Add this task card.
- Add a focused Tenn project-boundary doc under `docs/dev_flow/`.
- Update `docs/README.md` only to route operators to the project-boundary doc.
- Write report-local closeout files under this task `output_dir`.
- Run read-only guard, registry, ledger, grep, diff, and contract validation.
- After explicit owner approval, publish this Tenn docs-only branch by local
  commit, rebase onto canonical, branch push, and draft PR creation.

Forbidden:

- Tenn product, runtime, backend, extraction, parser, prompt, evaluator,
  source-PDF, gold-label, DB, Qdrant, Redis, news, memory, service, model,
  Docker, dependency, CI, or runtime artifact changes.
- Greyhound repo file edits, DB changes, systemd unit edits, service starts,
  restarts, stops, runtime artifact edits, branch/worktree changes, cleanup, or
  GitHub writes.
- Tenn merges, resets, stashes, branch deletion, worktree deletion, pruning,
  parked-work changes, or unrelated GitHub writes. Any Tenn commit, rebase,
  branch push, or draft PR creation must stay limited to this docs-only branch
  and require explicit owner approval.
- Broad repo cleanup or moving filesystem paths.

## Required Behavior

The docs must state:

- Tenn is the ASX financial ingestion, extraction, and cockpit workflow repo.
- Greyhound racing prediction/collector/runtime work is an external sibling
  project, even when a current filesystem path contains `tenn`.
- Greyhound work needs its own repo, task cards, reports, validation, and
  runtime proof.
- Tenn agents must not treat Greyhound repo dirt, services, DBs, artifacts, or
  branches as Tenn subsystem state.
- Any physical Greyhound relocation is a separate owner-approved runtime-proof
  workstream, not part of this docs-only task.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/greyhound_project_boundary_docs_v1_20260629.md`
- `python3 scripts/tenn_dev_status.py`
- `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /home/l4nd0/tenn-greyhound-project-boundary-docs-v1-20260629 --topic "Greyhound external sibling project docs boundary" --json`
- Focused grep proving the boundary terms appear only in allowed docs/report
  surfaces.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/greyhound_project_boundary_docs_v1_20260629.md --no-write-report`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/greyhound_project_boundary_docs_v1_20260629.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/greyhound_project_boundary_docs_v1_20260629.md --repo-root .`
- Final `git status --short --untracked-files=all`

## Closeout Notes

- This is docs-only and does not prove Tenn or Greyhound runtime
  functionality.
- Report-local closeout should record guard status, ledger/registry status,
  docs impact, model/worker routing, validation commands and results, unsafe
  actions avoided, and the next recommended prompt.
