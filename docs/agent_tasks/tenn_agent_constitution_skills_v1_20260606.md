---
job_id: tenn_agent_constitution_skills_v1_20260606
lane: Evaluation
supporting_lanes:
  - Repo Hygiene
  - Reporting
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/tenn_agent_constitution_skills_v1_20260606
mutation_mode: safe_extension
production_data_access: false
allowed_files:
  - docs/agent_tasks/tenn_agent_constitution_skills_v1_20260606.md
  - AGENTS.md
  - .agents/skills/tenn-financial-metric-extraction/SKILL.md
  - .agents/skills/tenn-task-card-registry-safety/SKILL.md
  - .agents/skills/tenn-goal-report/SKILL.md
  - reports/agent_jobs/tenn_agent_constitution_skills_v1_20260606/README.md
---

# Task

Rewrite Tenn `AGENTS.md` into a lean repo constitution and create the first
repo-backed Codex skill skeletons under `.agents/skills`.

Tracker: GitHub issue #78.

## Scope

- Replace stale Cursor Cloud-only AGENTS instructions with a short stable
  constitution.
- Create instruction-only skill skeletons:
  - `tenn-financial-metric-extraction`
  - `tenn-task-card-registry-safety`
  - `tenn-goal-report`
- Write the closeout report for this slice.

The task-card file itself is included in `allowed_files` because the local
`check-diff` gate compares all changed files literally against the allowlist.

## Hard Boundaries

- Do not touch product, backend, frontend, runtime, data, extraction, source
  PDF, gold-label, prompt, service config, or model/GPU/runtime state.
- Do not mutate DB, Qdrant, news, memory, backfills, or live services.
- Do not install dependencies.
- Do not create, edit, close, or comment on GitHub issues or PRs.
- Do not modify `.codex/hooks.json` or `.codex/config.toml`.
- Do not migrate all host skills.
- Do not clean, reset, stash, delete, rebase, merge, or prune unrelated dirt.

## Required Evidence

- `reports/agent_jobs/codex_agent_setup_audit_v1_20260606/README.md`
- Current `AGENTS.md`
- `.agents` and `.codex` inventory
- Task-card validator/registry script behavior
- Issue #78 metadata, read-only

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/tenn_agent_constitution_skills_v1_20260606.md`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/tenn_agent_constitution_skills_v1_20260606.md --no-write-report`
- `git diff --check`
- Manual markdown review of changed files
- `git status --short --untracked-files=all`

If `check-diff` fails only because of pre-existing unrelated dirty files outside
this allowlist, record the blocker in the closeout report and do not widen the
allowlist.

## Definition Of Done

- `AGENTS.md` contains the requested constitution sections.
- Repo skill skeletons exist under `.agents/skills`.
- `.codex/skills` is not used for new repo skills.
- Closeout report lists evidence, validation, remaining blockers, and next
  recommended prompt.
