---
job_id: tenn_auto_progress_phase1_readonly_planner_v1_20260610
lane: Evaluation
supporting_lanes:
  - Repo Hygiene
  - Reporting
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/tenn_auto_progress_phase1_readonly_planner_v1_20260610
mutation_mode: safe_extension
production_data_access: false
allowed_files:
  - docs/agent_tasks/tenn_auto_progress_phase1_readonly_planner_v1_20260610.md
  - .agents/skills/tenn-auto-progress/SKILL.md
  - reports/agent_jobs/tenn_auto_progress_phase1_readonly_planner_v1_20260610/README.md
  - reports/agent_jobs/tenn_auto_progress_phase1_readonly_planner_v1_20260610/ISSUE_SCAN.md
  - reports/agent_jobs/tenn_auto_progress_phase1_readonly_planner_v1_20260610/MILESTONE_SCAN.md
  - reports/agent_jobs/tenn_auto_progress_phase1_readonly_planner_v1_20260610/CANDIDATE_RANKINGS.md
  - reports/agent_jobs/tenn_auto_progress_phase1_readonly_planner_v1_20260610/MANDATE_CLASSIFICATION.md
  - reports/agent_jobs/tenn_auto_progress_phase1_readonly_planner_v1_20260610/CONTEXT_PACKS.md
  - reports/agent_jobs/tenn_auto_progress_phase1_readonly_planner_v1_20260610/DRAFT_TASK_CARDS.md
  - reports/agent_jobs/tenn_auto_progress_phase1_readonly_planner_v1_20260610/PHASE2_APPROVAL_MANIFEST.md
  - reports/agent_jobs/tenn_auto_progress_phase1_readonly_planner_v1_20260610/DATA_MISSING.md
  - reports/agent_jobs/tenn_auto_progress_phase1_readonly_planner_v1_20260610/VALIDATION.md
  - reports/agent_jobs/tenn_auto_progress_phase1_readonly_planner_v1_20260610/FRAME.md
  - reports/agent_jobs/tenn_auto_progress_phase1_readonly_planner_v1_20260610/STATE.md
  - reports/agent_jobs/tenn_auto_progress_phase1_readonly_planner_v1_20260610/OPERATOR_NOTES.md
---

# Tenn Auto Progress Phase 1 Readonly Planner V1

## Objective

Create the Phase 1 read-only planning surface for a Tenn Codex auto-progress
workflow, using issue #291 and the latest Codex loop-system audit as the source
of truth.

This is control-plane/dev-flow work only. It creates a repo-backed skill
skeleton and report-local planning artifacts. It stops before execution,
commits, GitHub writes, product/runtime/extraction validation, or live-system
mutation.

## Scope

Allowed:

- Add `.agents/skills/tenn-auto-progress/SKILL.md`.
- Read current AGENTS, Tenn skills, latest loop audit, GitHub issue #291, open
  issues, and milestones.
- Write the report bundle under the configured `output_dir`.
- Draft task-card packets inside the report bundle only.

Forbidden:

- Product, backend, frontend, runtime, data, extraction, source-PDF,
  gold-label, prompt, DB, Qdrant, Redis, news, memory, service, model/GPU,
  backfill, production-data, or live-service mutation.
- GitHub mutation: no comments, labels, closes, edits, PRs, or pushes.
- Commits, branch deletion, worktree removal, `git clean`, `git reset --hard`,
  stash/drop, rebase, merge, or cherry-pick.
- Product/runtime/extraction validation or service starts.

## Required Evidence

- `AGENTS.md`
- `.agents/skills/tenn-git-hygiene/SKILL.md`
- `.agents/skills/tenn-goal-report/SKILL.md`
- `.agents/skills/tenn-frame-design/SKILL.md`
- `reports/agent_jobs/codex_loop_system_status_audit_v1_20260608/README.md`
- `reports/agent_jobs/codex_loop_system_status_audit_v1_20260608/NEXT_IMPLEMENTATION_PLAN.md`
- GitHub issue #291 read-only evidence
- Open issues and milestones from read-only `gh` commands

## Required Output

- `README.md`
- `ISSUE_SCAN.md`
- `MILESTONE_SCAN.md`
- `CANDIDATE_RANKINGS.md`
- `MANDATE_CLASSIFICATION.md`
- `CONTEXT_PACKS.md`
- `DRAFT_TASK_CARDS.md`
- `PHASE2_APPROVAL_MANIFEST.md`
- `DATA_MISSING.md`
- `VALIDATION.md`

Frame artifacts are allowed because this is a `/goal` run.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/tenn_auto_progress_phase1_readonly_planner_v1_20260610.md`
- Verify all required report files exist.
- Whitespace-check generated markdown.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/tenn_auto_progress_phase1_readonly_planner_v1_20260610.md --no-write-report`
- Final `git status --short --untracked-files=all`
