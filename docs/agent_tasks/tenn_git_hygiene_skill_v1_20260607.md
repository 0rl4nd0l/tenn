---
job_id: tenn_git_hygiene_skill_v1_20260607
lane: Evaluation
supporting_lanes:
  - Repo Hygiene
  - Reporting
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/tenn_git_hygiene_skill_v1_20260607
mutation_mode: safe_extension
production_data_access: false
allowed_files:
  - docs/agent_tasks/tenn_git_hygiene_skill_v1_20260607.md
  - .agents/skills/tenn-git-hygiene/SKILL.md
  - reports/agent_jobs/tenn_git_hygiene_skill_v1_20260607/README.md
---

# Tenn Git Hygiene Skill v1

## Objective

Create a Tenn-native instruction-only Git Hygiene control-plane skill for
safely inspecting, classifying, preserving, integrating, and recommending
cleanup for Tenn Git branches, worktrees, dirty files, stale uncommitted work,
and merge/rebase candidates.

This is Tenn development workflow and control-plane infrastructure only. It is
not Tenn product, backend, frontend, runtime, data, extraction, model, GPU,
prompt, source-PDF, gold-label, DB, Qdrant, news, memory, service, or backfill
work.

## Scope

- Create `.agents/skills/tenn-git-hygiene/SKILL.md`.
- Create this task card.
- Create the closeout report under the allowed output directory.
- Keep the skill instruction-only. Do not add scripts, references,
  dependencies, agents, or assets.
- Do not update `tenn-frame-design` or `tenn-goal-report` unless a
  cross-reference is strictly needed.

## Required Skill Content

The skill must define:

- `AUDIT_ONLY`
- `REPORT_LOCAL`
- `PRESERVE_ONLY`
- `INTEGRATE_APPROVAL_REQUIRED`
- `CLEANUP_APPROVAL_REQUIRED`
- safety tiers 0-4
- required Tenn Git preflight commands
- dirty work age classification
- merge/rebase/cherry-pick rules
- Integration Plan requirements
- Scribe/Watcher report-only pattern
- report requirements
- validation requirements

## Hard Stops

- Do not touch product, backend, frontend, runtime, data, extraction, model,
  GPU, prompt, source-PDF, gold-label, DB, Qdrant, news, memory, services,
  production data, or backfills.
- Do not install dependencies.
- Do not push.
- Do not create, edit, close, comment on, or label GitHub issues or PRs.
- Do not run `git clean`, `git reset --hard`, `git stash drop`, branch
  deletion, worktree removal, rebase, merge, cherry-pick, force-push, or remote
  branch deletion.
- Do not clean or modify existing dirty worktrees.
- Do not widen this task-card allowlist.

## Required Evidence

- Current base: `origin/migration/clean-runtime-baseline-reconstruct-v1`.
- Existing repo skill conventions under `.agents/skills`.
- Existing task-card/report conventions under `docs/agent_tasks` and
  `reports/agent_jobs`.
- Registry read-only preflight:
  `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`.

## Validation

- Skill frontmatter parse for `name` and `description`.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/tenn_git_hygiene_skill_v1_20260607.md`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/tenn_git_hygiene_skill_v1_20260607.md --no-write-report`
- `git diff --check`
- Final `git status --short --untracked-files=all`

If validation fails due to unrelated existing dirt, record the blocker and do
not clean, stash, reset, delete, merge, rebase, or widen the allowlist.

## Definition Of Done

- Skill exists with required frontmatter and instruction-only body.
- Skill explicitly keeps Scribe/Watcher behavior report-only.
- Skill treats stale dirty work as unclassified work requiring preservation,
  ownership, or disposal decision.
- Task card validates.
- Check-diff shows only this bounded control-plane file set changed.
- Closeout report lists objective, files changed, exact skill summary, safety
  tiers, Scribe boundaries, approval gates, validation commands and exit status,
  unsafe actions avoided, and the next report-only Git hygiene audit prompt.
