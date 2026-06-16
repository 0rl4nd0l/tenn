---
job_id: dev_flow_operating_constitution_refinement_v1_20260616
lane: Evaluation
supporting_lanes:
  - Repo Hygiene
  - Reporting
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/dev_flow_operating_constitution_refinement_v1_20260616
mutation_mode: safe_extension
production_data_access: false
allowed_files:
  - AGENTS.md
  - .agents/skills/tenn-issue/SKILL.md
  - .agents/skills/tenn-review-board/SKILL.md
  - .agents/skills/tenn-fix/SKILL.md
  - .agents/skills/tenn-worker/SKILL.md
  - .agents/skills/tenn-explain/SKILL.md
  - .agents/skills/tenn-code-reviewer/SKILL.md
  - .agents/skills/tenn-improve-codebase-architecture/SKILL.md
  - .agents/skills/tenn-git-guard/SKILL.md
  - docs/dev_flow/templates/ISSUE.md
  - docs/dev_flow/templates/BOARD.md
  - docs/dev_flow/templates/BOARD_DECISION.json
  - docs/dev_flow/templates/EXPLAIN.md
  - docs/agent_tasks/dev_flow_operating_constitution_refinement_v1_20260616.md
  - reports/agent_jobs/dev_flow_operating_constitution_refinement_v1_20260616/README.md
  - reports/agent_jobs/dev_flow_operating_constitution_refinement_v1_20260616/AGENTS_UPDATES.md
  - reports/agent_jobs/dev_flow_operating_constitution_refinement_v1_20260616/SKILL_UPDATES.md
  - reports/agent_jobs/dev_flow_operating_constitution_refinement_v1_20260616/HOOK_INTEGRATION.md
  - reports/agent_jobs/dev_flow_operating_constitution_refinement_v1_20260616/VALIDATION.md
  - reports/agent_jobs/dev_flow_operating_constitution_refinement_v1_20260616/NEXT_STEPS.md
---

# Dev Flow Operating Constitution Refinement

## Objective

Refine Tenn's concise `AGENTS.md` constitution and native dev-flow wrapper
skills with the new operating principles for truthfulness, native Git Hygiene,
branch superiority checks, stale-work preservation, minimum necessary code,
review-board decisions, worker discipline, and explanation depth.

This is Tenn development workflow and control-plane work only.

## Scope

- Add a concise `Agent Operating Constitution` section to `AGENTS.md`.
- Add detailed behavior to the native dev-flow wrapper skills.
- Update only templates needed for safe decision defaults and evidence grades.
- Create this task card and the required report bundle.

## Hard Boundaries

- Do not touch product, runtime, data, extraction, model, GPU, prompt,
  source-PDF, gold-label, DB, Qdrant, Redis, news, memory, schema, services,
  production data, or backfills.
- Do not touch the count-24 extraction approval packet.
- Do not mutate host-global Codex files.
- Do not delete branches or worktrees.
- Do not run broad validation or start services.
- Do not clean, reset, stash, merge, rebase, cherry-pick, force-push, or prune.
- Do not mutate GitHub except opening the PR after local validation passes.
- Do not implement scripts in this run.

## Required Evidence

- PR #355 state is merged before proceeding.
- Current base and clean sibling worktree evidence.
- Wrapper skills exist on current base.
- Read-only registry evidence.
- Read-only related PR, branch, and worktree audit for advanced existing work.
- Audit bundle:
  `reports/agent_jobs/dev_flow_ground_up_reset_audit_v1_20260616/`.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/dev_flow_operating_constitution_refinement_v1_20260616.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- Parse/check all changed `SKILL.md` files.
- Validate changed JSON templates with `python3 -m json.tool`.
- `git diff --check`
- Changed-path guard proving only allowlisted control-plane docs, skills, task,
  templates, and report paths changed.
- Confirm no product/runtime/data/extraction paths changed.
- Confirm no host-global files changed.
- Confirm no count-24 packet touched.
- Final status.

## Definition Of Done

- `AGENTS.md` has concise constitutional rules.
- Wrapper skills contain detailed behavior.
- Existing host goal optimizer and stop hooks are recognized as backend guards,
  not reimplemented.
- Git Hygiene, truthfulness, branch superiority, stale-work preservation,
  minimal-code, and no-report-loop policies are encoded.
- Validation passes, a local commit exists, and a PR is open but not merged.
