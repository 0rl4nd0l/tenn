---
job_id: tenn_frame_design_skill_v1_20260607
lane: Evaluation
supporting_lanes:
  - Repo Hygiene
  - Reporting
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/tenn_frame_design_skill_v1_20260607
mutation_mode: safe_extension
production_data_access: false
allowed_files:
  - docs/agent_tasks/tenn_frame_design_skill_v1_20260607.md
  - .agents/skills/tenn-frame-design/SKILL.md
  - .agents/skills/tenn-goal-report/SKILL.md
  - reports/agent_jobs/tenn_frame_design_skill_v1_20260607/README.md
---

# Task

Create a Tenn-native Frame Design control-plane skill for long-running `/goal`
work and lightly update the Tenn goal-report skill to reference Frame and
Operator Notes artifacts.

## Scope

- Create `.agents/skills/tenn-frame-design/SKILL.md`.
- Update `.agents/skills/tenn-goal-report/SKILL.md` only as needed to reference
  `FRAME.md`, `STATE.md`, `OPERATOR_NOTES.md`, and optional `SCRIBE.md`.
- Write the closeout report under
  `reports/agent_jobs/tenn_frame_design_skill_v1_20260607/README.md`.

## Hard Boundaries

- Do not touch product, backend, frontend, runtime, data, extraction, source
  PDFs, gold labels, prompts, services, model/GPU/runtime config, or production
  data.
- Do not mutate DB, Qdrant, news, memory, backfills, source PDFs, gold labels,
  prompts, services, runtime/model/GPU config, or production data.
- Do not install dependencies.
- Do not push.
- Do not create, edit, close, comment on, or reopen GitHub issues or PRs.
- Do not copy Loopgen or third-party skill text.
- Keep this Tenn-native and instruction-only.

## Required Evidence

- Current branch, HEAD, upstream, origin, and dirty-state proof.
- Read-only registry `list-active` proof.
- Current `AGENTS.md`.
- Existing Tenn skills:
  - `.agents/skills/tenn-goal-report/SKILL.md`
  - `.agents/skills/tenn-task-card-registry-safety/SKILL.md`
  - `.agents/skills/tenn-financial-metric-extraction/SKILL.md`

## Required Validation

- Skill frontmatter parse.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/tenn_frame_design_skill_v1_20260607.md`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/tenn_frame_design_skill_v1_20260607.md --no-write-report`
- `git diff --check`
- Final `git status --short --untracked-files=all`

## Definition Of Done

- `tenn-frame-design` exists and defines the compact Frame and optional Scribe
  pattern.
- `tenn-goal-report` references Frame and Operator Notes only where useful.
- The report lists objective, changed files, product-readiness rationale, exact
  Frame schema, Scribe boundaries, validation commands with exit status, unsafe
  actions avoided, and the next recommended product-focused `/goal` prompt.
