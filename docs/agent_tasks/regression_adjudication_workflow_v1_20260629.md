---
job_id: regression_adjudication_workflow_v1_20260629
lane: Reporting
supporting_lanes:
  - Evaluation
  - Provenance
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/regression_adjudication_workflow_v1_20260629
mutation_mode: safe_extension
production_data_access: false
task_scope: control_plane_only
closeout_scope: control_plane_only
allowed_files:
  - docs/agent_tasks/regression_adjudication_workflow_v1_20260629.md
  - docs/dev_flow/REGRESSION_ADJUDICATION.md
  - docs/dev_flow/SKILLS_SURFACE.md
  - .agents/skills/tenn-fix/SKILL.md
  - .agents/skills/tenn-review-board/SKILL.md
---

# Regression Adjudication Workflow

## Objective

Add a Tenn control-plane workflow for resurfacing bugs so agents classify
whether the problem is stale branch state, missing canonical integration,
narrow prior scope, missing runtime proof, missing tests, a new failure class,
or a true regression before coding another fix.

## Scope

Allowed:

- Add the regression adjudication workflow under `docs/dev_flow/`.
- Wire `tenn-fix` and `tenn-review-board` to require the workflow for
  "fixed already", "broken again", or regression-style prompts.
- Update `docs/dev_flow/SKILLS_SURFACE.md` to route this as a mode of existing
  skills, not a new visible skill.

Forbidden:

- Product, runtime, extraction, parser, prompt, source-PDF, gold-label, DB,
  Qdrant, Redis, news, memory, model/GPU, service, GitHub, branch, worktree, or
  registry mutation.
- Cleanup, reset, stash, rebase, merge, cherry-pick, push, or issue mutation.
- Editing `AGENTS.md`; this task keeps repeatable procedure in focused
  dev-flow docs and repo-backed skills.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/regression_adjudication_workflow_v1_20260629.md`
- Focused markdown/diff review of the allowed files.
- `git diff --check -- docs/agent_tasks/regression_adjudication_workflow_v1_20260629.md docs/dev_flow/REGRESSION_ADJUDICATION.md docs/dev_flow/SKILLS_SURFACE.md .agents/skills/tenn-fix/SKILL.md .agents/skills/tenn-review-board/SKILL.md`
- Confirm no product/runtime/extraction/data files changed.

## Definition Of Done

- Resurfacing bug prompts have a required adjudication flow before
  implementation.
- The workflow defines exact classifications and next actions.
- Existing skill routing points at the workflow without adding a new visible
  skill.
