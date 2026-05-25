---
schema_version: goal_schema_v1
goal_id: example_goal_v1
status: draft
owner: Codex
mode: safe_extension
objective: Add a bounded repo-native orchestration slice.
primary_lane: Reporting
supporting_lanes:
  - Evaluation
task_card: docs/agent_tasks/example_goal_task_v1.md
output_dir: reports/agent_jobs/example_goal_task_v1
validation:
  - python3 scripts/agent_job_contract.py validate docs/agent_tasks/example_goal_task_v1.md
  - python3 scripts/agent_goal_contract.py validate docs/goals/_template.md
hard_stops:
  - Stop if active registry jobs overlap allowed files.
  - Stop if the change needs product or runtime implementation.
merge_parking_status: not_implemented
save_recommendation: Run /save only after task-card validation, focused tests, and report artifacts are complete.
---

# Goal: Example Goal v1

## Objective

Describe the parent objective. Keep this to the business or orchestration
outcome, not the implementation details of one task card.

## Lanes

- Primary lane: Reporting
- Supporting lanes: Evaluation

## Task Card

- Current task card: `docs/agent_tasks/example_goal_task_v1.md`
- Task cards remain the source of `allowed_files`, registry ownership, overlap
  checks, and `check-diff` enforcement.

## Output Dir

`reports/agent_jobs/example_goal_task_v1`

## Validation

- Validate the task card.
- Run registry `list-active` and `check-overlap`.
- Run focused tests for changed code.
- Run `python3 scripts/agent_goal_contract.py validate --changed`.
- Run `git diff --check`.
- Run task-card `check-diff`.

## Hard Stops

- Stop if active jobs overlap the task card, output directory, or intended
  files.
- Stop if the work would touch forbidden product, runtime, financial-truth,
  memory, database, Qdrant, parser, extraction, Docker, model, or GPU surfaces.

## Merge Parking Status

Not implemented in this slice. Document readiness only; do not create parking
branches, Git-ref claims, auto-merge, cherry-pick, rebase, reset, stash, or
cleanup automation from this goal file.

## Save Recommendation

Run `/save` only after the task-card job has a complete report, validation
evidence, and no unresolved hard blockers.
