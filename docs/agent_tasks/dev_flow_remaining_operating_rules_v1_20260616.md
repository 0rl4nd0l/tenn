---
job_id: dev_flow_remaining_operating_rules_v1_20260616
lane: Evaluation
supporting_lanes:
  - Repo Hygiene
  - Reporting
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/dev_flow_remaining_operating_rules_v1_20260616
mutation_mode: safe_extension
production_data_access: false
allowed_files:
  - docs/agent_tasks/dev_flow_remaining_operating_rules_v1_20260616.md
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
  - docs/dev_flow/templates/MILESTONES.md
  - docs/dev_flow/templates/BOARD.md
  - docs/dev_flow/templates/BOARD_DECISION.json
  - docs/dev_flow/templates/NEXT_GOAL.md
  - docs/dev_flow/templates/STATE.md
  - docs/dev_flow/templates/WORKER_RESULT.md
  - docs/dev_flow/templates/PR_REVIEW.md
  - docs/dev_flow/templates/DECISIONS.md
  - docs/dev_flow/templates/EXPLAIN.md
  - docs/dev_flow/templates/TASK_LEDGER_ENTRY.json
  - docs/dev_flow/templates/TASK_LEDGER_SUMMARY.md
  - docs/dev_flow/templates/COUNTER_LINEAGE.md
  - docs/agent_registry/task_ledger/README.md
  - reports/agent_jobs/dev_flow_remaining_operating_rules_v1_20260616/README.md
  - reports/agent_jobs/dev_flow_remaining_operating_rules_v1_20260616/AGENTS_UPDATES.md
  - reports/agent_jobs/dev_flow_remaining_operating_rules_v1_20260616/SKILL_UPDATES.md
  - reports/agent_jobs/dev_flow_remaining_operating_rules_v1_20260616/TEMPLATE_UPDATES.md
  - reports/agent_jobs/dev_flow_remaining_operating_rules_v1_20260616/HOOK_INTEGRATION.md
  - reports/agent_jobs/dev_flow_remaining_operating_rules_v1_20260616/VALIDATION.md
  - reports/agent_jobs/dev_flow_remaining_operating_rules_v1_20260616/NEXT_STEPS.md
---

# Dev Flow Remaining Operating Rules V1

## Objective

Encode remaining Tenn hands-off dev-flow operating rules into concise
constitution text, wrapper-skill behavior, and reusable templates.

This is control-plane docs/skills/templates work only.

## Scope

- Add missing truthfulness, `DATA_MISSING`, counter-lineage, and
  surprising-number rules.
- Strengthen wrapper skills for ledger-aware duplicate prevention, smallest safe
  diffs, review-board discipline, worker discipline, and architecture planning.
- Add or update templates needed by future agents.
- Create this task card and report bundle.

## Hard Boundaries

- Do not touch product, runtime, data, extraction, source-PDF, gold-label, DB,
  Qdrant, Redis, news, memory, prompt, schema, service, model, GPU, or count-24
  implementation paths.
- Do not implement a ledger script.
- Do not mutate host-global files.
- Do not delete branches or worktrees.
- Do not run cleanup, broad validation, merge, rebase, cherry-pick, reset,
  stash, clean, force-push, or prune.
- Do not mutate GitHub except opening the approved PR after validation.
- Do not merge the PR.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/dev_flow_remaining_operating_rules_v1_20260616.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- Parse/check all changed `SKILL.md` files.
- Validate changed JSON templates with `python3 -m json.tool`.
- `git diff --check`
- Changed-path guard proving only approved control-plane docs, skills,
  templates, task-card, and report paths changed.
- Product/runtime/data/extraction guard.
- count-24 guard.
- Host-global guard.
- Final status.

## Definition Of Done

- `AGENTS.md` includes concise remaining constitutional rules.
- Wrapper skills contain detailed behavior.
- Agent Task Ledger and counter-lineage rules are encoded.
- Existing host goal optimizer is referenced as a backend guard, not
  reimplemented.
- PR is open and unmerged against
  `migration/clean-runtime-baseline-reconstruct-v1`.
