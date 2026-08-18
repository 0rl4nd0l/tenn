---
job_id: two_shot_dev_flow_control_surface_v1_20260607
lane: Evaluation
supporting_lanes:
  - Repo Hygiene
  - Reporting
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/two_shot_dev_flow_control_surface_v1_20260607
mutation_mode: safe_extension
production_data_access: false
allowed_files:
  - docs/agent_tasks/two_shot_dev_flow_control_surface_v1_20260607.md
  - AGENTS.md
  - .agents/skills/tenn-git-hygiene/SKILL.md
  - .agents/skills/tenn-goal-report/SKILL.md
  - .agents/skills/tenn-frame-design/SKILL.md
  - reports/agent_jobs/two_shot_dev_flow_control_surface_v1_20260607/README.md
---

# Two-Shot Dev-Flow Control Surface V1

## Objective

Update Tenn development workflow and control-plane guidance so non-trivial Git
Hygiene and control-plane remediation default to two-shot workstreams with clear
autonomy profiles.

This is Tenn development workflow/control-plane work only. It is not Tenn
product, backend, frontend, runtime, data, extraction, model, GPU, prompt,
source-PDF, gold-label, DB, Qdrant, news, memory, service, or backfill work.

## Scope

- Add a concise two-shot/autonomy rule to `AGENTS.md`.
- Add detailed autonomy profiles and two-shot execution rules to
  `.agents/skills/tenn-git-hygiene/SKILL.md`.
- Add minimal cross-references to `tenn-goal-report` and `tenn-frame-design`.
- Create this task card and the closeout report under the allowed output
  directory.

## Hard Boundaries

- Do not touch product, backend, frontend, runtime, data, extraction, model,
  GPU, prompt, source-PDF, gold-label, DB, Qdrant, news, memory, services,
  production data, or backfills.
- Do not install dependencies.
- Do not mutate DB, Qdrant, news, memory, backfills, source PDFs, gold labels,
  prompts, services, runtime/model/GPU config, production data, or live
  services.
- Do not run `git clean`, `git reset --hard`, stash or stash drop, branch
  deletion, worktree removal, rebase, merge, cherry-pick, push, force-push, or
  GitHub mutation.
- Do not start another Git Hygiene cleanup wave.
- Do not alter dirty live branches or widen this task-card allowlist.

## Required Evidence

- Current repo path, branch, HEAD, upstream, origin, and status.
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
  when available.
- Existing `AGENTS.md`.
- Existing Tenn skills:
  - `.agents/skills/tenn-git-hygiene/SKILL.md`
  - `.agents/skills/tenn-goal-report/SKILL.md`
  - `.agents/skills/tenn-frame-design/SKILL.md`
- Two-shot evidence under
  `reports/agent_jobs/live_branch_two_shot_remediation_manifest_v1_20260607/`
  from the dirty source checkout.

## Required Validation

- Skill frontmatter parse.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/two_shot_dev_flow_control_surface_v1_20260607.md`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/two_shot_dev_flow_control_surface_v1_20260607.md --no-write-report`
- `git diff --check`
- Changed-path guard proving no product/runtime/extraction paths changed.
- Final `git status --short --untracked-files=all`.

## Definition Of Done

- `AGENTS.md` includes the two-shot/autonomy law.
- `tenn-git-hygiene` includes detailed autonomy profiles.
- Cross-references are minimal and scoped.
- Validation passes.
- Closeout report lists evidence, changed files, validation, unsafe actions
  avoided, readiness for commit/PR, and the next recommended step.
- Local commit exists if validation passes and changed files are exactly
  allowlisted.
