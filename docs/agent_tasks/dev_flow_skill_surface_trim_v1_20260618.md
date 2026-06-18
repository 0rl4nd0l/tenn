---
job_id: dev_flow_skill_surface_trim_v1_20260618
lane: Reporting
supporting_lanes:
  - Repo Hygiene
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/dev_flow_skill_surface_trim_v1_20260618
mutation_mode: safe_extension
production_data_access: false
allowed_files:
  - docs/agent_tasks/dev_flow_skill_surface_trim_v1_20260618.md
  - .agents/skills/tenn-auto-progress/SKILL.md
  - .agents/skills/tenn-frame-design/SKILL.md
  - .agents/skills/tenn-git-hygiene/SKILL.md
  - .agents/skills/tenn-worker/SKILL.md
  - .agents/skills/tenn-code-reviewer/SKILL.md
  - .agents/skills/tenn-task-card-registry-safety/SKILL.md
  - .agents/skills/tenn-issue/SKILL.md
  - .agents/skills/tenn-fix/SKILL.md
  - .agents/skills/tenn-git-guard/SKILL.md
  - .agents/skills/tenn-goal-report/SKILL.md
  - .agents/skills/tenn-improve-codebase-architecture/SKILL.md
  - docs/dev_flow/SKILLS_SURFACE.md
  - docs/dev_flow/templates/FRAME.md
  - docs/dev_flow/templates/OPERATOR_NOTES.md
  - docs/dev_flow/templates/WORKER_TASK.md
  - docs/dev_flow/templates/WORKER_RESULT.md
  - docs/dev_flow/templates/PR_REVIEW.md
  - reports/agent_jobs/dev_flow_skill_surface_trim_v1_20260618/README.md
  - reports/agent_jobs/dev_flow_skill_surface_trim_v1_20260618/VALIDATION.md
  - reports/agent_jobs/dev_flow_skill_surface_trim_v1_20260618/PR_REVIEW.md
  - reports/agent_jobs/dev_flow_skill_surface_trim_v1_20260618/handoff/HANDOFF.md
  - reports/agent_jobs/dev_flow_skill_surface_trim_v1_20260618/handoff/NEXT_GOAL.md
  - reports/agent_jobs/dev_flow_skill_surface_trim_v1_20260618/handoff/LEDGER_ENTRY.json
---

# Dev Flow Skill Surface Trim V1

## Objective

Continue the Tenn/Codex skill context bloat trim from fresh canonical
`acb7e9a7df6a9b75d14beff16c750693a4aab5e6`. Use the preserved
`dev_flow_skills_bloat_audit_v1_20260617` bundle as evidence. Treat PR #367 as
superseded by PR #375 and do not merge it.

## Scope

- Remove selected broad/backend repo skill entrypoints from the visible
  `.agents/skills/*/SKILL.md` surface.
- Merge or rehome their durable behavior into core visible skills, docs, and
  templates.
- Add `docs/dev_flow/SKILLS_SURFACE.md` as the operator/backend surface map.
- Add lightweight validation that the trimmed skill entrypoints are gone, core
  skill H1s remain valid, and no forbidden path class changed.

## Hard Boundaries

- Do not touch product, runtime, data, extraction, source-PDF, gold-label,
  prompt, schema, service, model, GPU, DB, Qdrant, Redis, news, memory, or
  count-24 paths.
- Do not mutate host-global files under `/home/l4nd0/.codex`,
  `/home/l4nd0/.agents`, plugin cache directories, or any home-directory skill
  roots.
- Do not merge, adopt, or update PR #367.
- Do not clean, delete branches, remove worktrees, merge, rebase, reset, stash,
  cherry-pick, prune, or force-push.
- Push this branch and open a focused PR only because the owner explicitly
  approved that follow-through after local implementation review.
- Do not install dependencies, start services, or run runtime/product
  validation.

## Preflight Evidence Required

- Fresh worktree, branch, HEAD, origin, upstream status, dirty state, selected
  base, and merge base.
- Read-only registry state.
- Live and committed task-ledger availability.
- Handoff template/skill availability.
- Duplicate-work classification for PR #367 and PR #375.
- Preserved audit bundle paths and recommendations.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/dev_flow_skill_surface_trim_v1_20260618.md`
- `python3 scripts/agent_task_ledger.py resolve-path`
- `python3 scripts/agent_task_ledger.py validate`
- Lightweight skill-surface check for trimmed entrypoints and core H1s.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/dev_flow_skill_surface_trim_v1_20260618.md --no-write-report`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/dev_flow_skill_surface_trim_v1_20260618.md`
- Product/runtime/data/extraction/count-24 guard.
- Host-global guard.
- Final `git status --short --untracked-files=all`.

## Definition Of Done

- The visible repo skill surface is smaller and documented.
- `tenn-auto-progress`, `tenn-frame-design`, `tenn-git-hygiene`,
  `tenn-worker`, `tenn-code-reviewer`, and `tenn-task-card-registry-safety`
  are rehomed or merged without deleting historical evidence.
- `tenn-goal-report` remains a compact `/goal` backend with optional frame
  mode through templates.
- No product/runtime/extraction/data/count-24 or host-global mutation occurred.
