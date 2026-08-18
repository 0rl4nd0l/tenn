---
job_id: dev_flow_dirty_branch_classification_v1_20260618
lane: Evaluation
supporting_lanes:
  - Repo Hygiene
  - Reporting
owner: Codex
approval_required: false
allow_audit_code_changes: true
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/dev_flow_dirty_branch_classification_v1_20260618
mutation_mode: safe_extension
production_data_access: false
allowed_files:
  - docs/agent_tasks/validation_environment_autonomy_skill_update_v1_20260617.md
  - .agents/skills/tenn-fix/SKILL.md
  - .agents/skills/tenn-worker/SKILL.md
  - .agents/skills/tenn-git-guard/SKILL.md
  - reports/agent_jobs/dev_flow_dirty_branch_classification_v1_20260618/README.md
  - reports/agent_jobs/dev_flow_dirty_branch_classification_v1_20260618/PR_STATE.md
  - reports/agent_jobs/dev_flow_dirty_branch_classification_v1_20260618/DIRTY_FILES.md
  - reports/agent_jobs/dev_flow_dirty_branch_classification_v1_20260618/CLASSIFICATION.md
  - reports/agent_jobs/dev_flow_dirty_branch_classification_v1_20260618/NOVEL_DIFFS.md
  - reports/agent_jobs/dev_flow_dirty_branch_classification_v1_20260618/NEXT_ACTION.md
  - reports/agent_jobs/dev_flow_dirty_branch_classification_v1_20260618/VALIDATION.md
---

# Validation Environment Autonomy Skill Update V1

## Objective

Preserve the genuinely novel validation-environment autonomy guidance from the
old dirty branch after comparing it against current canonical and recent
control-plane PRs.

## Scope

- Add concise validation environment autonomy guidance to `tenn-fix`,
  `tenn-worker`, and `tenn-git-guard`.
- Preserve the old branch's useful intent without replaying stale hunks that
  remove the docs-impact and model-routing guidance merged by PR #368.
- Create the required dirty-branch classification report bundle.

## Hard Boundaries

- Do not touch product, runtime, data, extraction, source-PDF, gold-label,
  prompt, schema, service, model, GPU, DB, Qdrant, Redis, news, memory, or
  count-24 paths.
- Do not mutate host-global files, runtime venvs, project dependencies,
  lockfiles, CI config, services, or system packages.
- Do not clean, delete, merge, rebase, reset, stash, cherry-pick, prune, or
  force-push the original dirty checkout.
- Do not mix this with OpenCode bridge work or create new broad skills.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/validation_environment_autonomy_skill_update_v1_20260617.md`
- Parse changed `SKILL.md` frontmatter/H1.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/validation_environment_autonomy_skill_update_v1_20260617.md --no-write-report`
- Product/runtime/data/extraction/count-24 guard.
- Final `git status --short --untracked-files=all`.

## Definition Of Done

- Every dirty file from the old checkout is classified.
- The merged skills-bloat task card is not recommitted.
- The validation environment autonomy guidance is preserved as an additive
  canonical patch.
- No project dependency, runtime venv, CI, product/runtime/data/extraction,
  host-global, or original dirty-checkout files are changed.
