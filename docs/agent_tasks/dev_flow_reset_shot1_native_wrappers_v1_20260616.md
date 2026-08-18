---
job_id: dev_flow_reset_shot1_native_wrappers_v1_20260616
lane: Evaluation
supporting_lanes:
  - Repo Hygiene
  - Reporting
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/dev_flow_reset_shot1_native_wrappers_v1_20260616
mutation_mode: safe_extension
production_data_access: false
allowed_files:
  - docs/agent_tasks/dev_flow_reset_shot1_native_wrappers_v1_20260616.md
  - .agents/skills/tenn-issue/SKILL.md
  - .agents/skills/tenn-review-board/SKILL.md
  - .agents/skills/tenn-fix/SKILL.md
  - .agents/skills/tenn-worker/SKILL.md
  - .agents/skills/tenn-explain/SKILL.md
  - .agents/skills/tenn-code-reviewer/SKILL.md
  - .agents/skills/tenn-improve-codebase-architecture/SKILL.md
  - .agents/skills/tenn-git-guard/SKILL.md
  - docs/dev_flow/templates/ISSUE.md
  - docs/dev_flow/templates/MILESTONES.md
  - docs/dev_flow/templates/BOARD.md
  - docs/dev_flow/templates/BOARD_DECISION.json
  - docs/dev_flow/templates/NEXT_GOAL.md
  - docs/dev_flow/templates/STATE.md
  - docs/dev_flow/templates/WORKER_RESULT.md
  - docs/dev_flow/templates/PR_REVIEW.md
  - docs/dev_flow/templates/DECISIONS.md
  - docs/dev_flow/templates/EXPLAIN.md
  - reports/agent_jobs/dev_flow_reset_shot1_native_wrappers_v1_20260616/README.md
  - reports/agent_jobs/dev_flow_reset_shot1_native_wrappers_v1_20260616/AUDIT_INPUTS.md
  - reports/agent_jobs/dev_flow_reset_shot1_native_wrappers_v1_20260616/IMPLEMENTATION.md
  - reports/agent_jobs/dev_flow_reset_shot1_native_wrappers_v1_20260616/SKILL_SUMMARY.md
  - reports/agent_jobs/dev_flow_reset_shot1_native_wrappers_v1_20260616/TEMPLATES.md
  - reports/agent_jobs/dev_flow_reset_shot1_native_wrappers_v1_20260616/VALIDATION.md
  - reports/agent_jobs/dev_flow_reset_shot1_native_wrappers_v1_20260616/NEXT_STEPS.md
---

# Dev Flow Reset Shot 1 Native Wrappers

## Objective

Create instruction-only Tenn wrapper skills and minimal artifact templates for
the hands-off development workflow described in the dev-flow ground-up reset
audit.

This is Tenn development workflow and control-plane work only. It is not Tenn
product, backend, frontend, runtime, data, extraction, model, GPU, prompt,
source-PDF, gold-label, DB, Qdrant, Redis, news, memory, service, schema, or
backfill work.

## Scope

- Add repo-local wrapper skills for `tenn-issue`, `tenn-review-board`,
  `tenn-fix`, `tenn-worker`, `tenn-explain`, `tenn-code-reviewer`,
  `tenn-improve-codebase-architecture`, and `tenn-git-guard`.
- Add minimal templates for `ISSUE.md`, `MILESTONES.md`, `BOARD.md`,
  `BOARD_DECISION.json`, `NEXT_GOAL.md`, `STATE.md`, `WORKER_RESULT.md`,
  `PR_REVIEW.md`, `DECISIONS.md`, and `EXPLAIN.md`.
- Create the required report bundle under `output_dir`.

## Hard Boundaries

- Do not remove, rename, or rewrite existing skills.
- Do not implement cleanup, execution automation, worker spawning scripts, or
  host-global hook changes.
- Do not touch product, runtime, data, extraction, model, GPU, prompt,
  source-PDF, gold-label, DB, Qdrant, Redis, news, memory, schema, services,
  production data, or backfills.
- Do not touch the count-24 extraction approval packet.
- Do not mutate host-global Codex files.
- Do not run broad validation or start services.
- Do not clean, reset, stash, merge, rebase, cherry-pick, force-push, prune,
  delete branches, or delete worktrees.
- Do not mutate GitHub until local validation passes and the PR is opened.

## Required Evidence

- Current repo path, branch, HEAD, origin, upstream, and status.
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
  when available.
- Audit bundle:
  `reports/agent_jobs/dev_flow_ground_up_reset_audit_v1_20260616/`.
- Existing repo skills and task-card contract script.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/dev_flow_reset_shot1_native_wrappers_v1_20260616.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- Parse/check every new `SKILL.md`.
- Verify all required wrapper skills exist.
- Verify all required templates exist.
- `git diff --check`
- Changed-path guard proving only allowed control-plane docs, skills, task card,
  and report paths changed.
- Confirm no product/runtime/data/extraction paths changed.
- Confirm no host-global files changed.
- Confirm no GitHub mutation before PR creation.

## Definition Of Done

- New instruction-only Tenn wrapper skills exist.
- Existing `diagnose` is preserved and wrapped, not replaced.
- Git Hygiene is represented as the `tenn-git-guard` backend.
- `/issue -> /review-board -> /fix` is documented as the canonical hands-off
  workflow.
- Operator workflow is clearer and less bloated.
- No product/runtime/extraction mutation occurred.
- Validation passes, a local commit exists, and a PR is open but not merged.
