---
job_id: control_plane_orlando_audit_v1_20260622
lane: Reporting
supporting_lanes:
  - Repo Hygiene
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/control_plane_orlando_audit_v1_20260622
mutation_mode: safe_extension
production_data_access: false
allowed_files:
  - docs/agent_tasks/control_plane_orlando_audit_v1_20260622.md
  - docs/dev_flow/CONTROL_PLANE_STATUS.md
  - docs/dev_flow/GOAL_AND_MONITOR_RUNBOOK.md
  - docs/dev_flow/OPENCODE_WORKER_BRIDGE_RUNBOOK.md
  - docs/dev_flow/CODEX_OPERATOR_GUIDE.md
  - docs/dev_flow/CONTROL_PLANE_OPEN_WORK.md
  - reports/agent_jobs/control_plane_orlando_audit_v1_20260622/README.md
  - reports/agent_jobs/control_plane_orlando_audit_v1_20260622/PREFLIGHT.md
  - reports/agent_jobs/control_plane_orlando_audit_v1_20260622/CONTROL_PLANE_INVENTORY.md
  - reports/agent_jobs/control_plane_orlando_audit_v1_20260622/RECENT_WORK_SEARCH.md
  - reports/agent_jobs/control_plane_orlando_audit_v1_20260622/OPENCODE_PROBE.txt
  - reports/agent_jobs/control_plane_orlando_audit_v1_20260622/SKILL_CHECKS.md
  - reports/agent_jobs/control_plane_orlando_audit_v1_20260622/VALIDATION.md
  - reports/agent_jobs/control_plane_orlando_audit_v1_20260622/PR_REVIEW.md
---

# Control Plane Orlando Audit V1

## Objective

Run a full Tenn/Codex control-plane audit from current canonical after PR #380
and PR #382, then produce a practical operator guide for Orlando.

## Scope

- Audit control-plane docs, repo-backed skills, templates, scripts, hooks, task
  cards, registry/ledger behavior, report bundles, and recent control-plane
  PR/report evidence.
- Document what is implemented, partial, doc-only, host-only, missing, stale,
  superseded, or unknown.
- Document `/goal`, goal-report, monitor concepts, OpenCode worker bridge usage,
  day-to-day Codex operation, unfinished work, and the implementation truth
  table.
- Run the safe OpenCode worker bridge probe and report the exact result.
- Make only docs/report/task-card changes.

## Hard Boundaries

- Do not touch Tenn product, runtime, data, extraction, source-PDF, gold-label,
  prompt, schema, service, model, GPU, DB, Qdrant, Redis, news, memory, or
  count-24 paths.
- Do not touch greyhound runtime.
- Do not mutate host-global Codex files under `/home/l4nd0/.codex`,
  `/home/l4nd0/.agents`, plugin cache directories, or any home-directory skill
  roots.
- Do not delete branches or worktrees.
- Do not merge, rebase, cherry-pick, reset, stash, clean, prune, or force-push.
- Do not create, edit, comment on, close, reopen, or label GitHub issues.
- Do not implement new runtime, monitor, automation, or hook machinery.
- Do not claim runtime functionality unless Runtime Functionality Proof applies
  and is proven.

## GitHub Boundary

After validation passes, pushing this branch and opening one focused PR for the
docs/report audit is permitted. No other GitHub write action is permitted.

## Required Preflight

- Print `pwd`, branch, HEAD, upstream, git status, and canonical origin HEAD.
- Read `AGENTS.md` fully.
- Read `docs/dev_flow/SKILLS_SURFACE.md` fully.
- List `.agents/skills/*/SKILL.md` and verify the visible count is still 10.
- Check active registry read-only.
- Check task ledger read-only/validate.
- Search recent control-plane reports, task cards, PRs, and branches for
  unfinished or superseded work.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/control_plane_orlando_audit_v1_20260622.md`
- `python3 scripts/agent_task_ledger.py resolve-path`
- `python3 scripts/agent_task_ledger.py validate`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `find .agents/skills -maxdepth 2 -name SKILL.md | sort | wc -l`
- Skill frontmatter/H1 check for visible repo skills.
- `python3 scripts/opencode_worker_bridge.py probe`
- Docs links/path checks if available, otherwise a bounded path-existence check
  over referenced repo paths.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/control_plane_orlando_audit_v1_20260622.md --no-write-report`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/control_plane_orlando_audit_v1_20260622.md`
- Product/runtime/data/extraction/count-24 guard.
- Host-global guard.
- Final `git status --short --untracked-files=all`.

## Definition Of Done

- Requested docs exist:
  - `docs/dev_flow/CONTROL_PLANE_STATUS.md`
  - `docs/dev_flow/GOAL_AND_MONITOR_RUNBOOK.md`
  - `docs/dev_flow/OPENCODE_WORKER_BRIDGE_RUNBOOK.md`
  - `docs/dev_flow/CODEX_OPERATOR_GUIDE.md`
  - `docs/dev_flow/CONTROL_PLANE_OPEN_WORK.md`
- Report bundle captures preflight, inventory, recent-work search, OpenCode
  probe, skill checks, validation, and review evidence.
- The audit distinguishes implemented behavior from doc-only, host-only,
  missing, stale, superseded, and unknown behavior.
- No forbidden product/runtime/data/extraction/count-24, greyhound, or
  host-global files changed.
