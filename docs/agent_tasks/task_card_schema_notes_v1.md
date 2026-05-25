# Task-Card Schema Notes v1

This note records the current task-card validator shape and the gap addressed
by the first repo-native goal/status schema slice. It is documentation only; it
does not change `scripts/agent_job_contract.py`.

## Current Validator

`scripts/agent_job_contract.py validate <task_card>` validates Markdown files
with YAML frontmatter. The current required frontmatter fields are:

- `job_id`
- `lane`
- `owner`
- `allowed_files`
- `approval_required`
- `timeout_seconds`
- `output_dir`
- `mutation_mode`
- `production_data_access`

Current enforced values and rules include:

- `lane` must be one of `Financial Truth`, `Evaluation`, `Provenance`,
  `Query Orchestration`, `Memory`, or `Reporting`.
- `mutation_mode` must be `audit_only`, `safe_extension`, or `blocked`.
- `production_data_access` must be literal `false`.
- `safe_extension` jobs require `approval_required: true` unless
  `allow_unapproved_safe_extension: true` is present.
- `output_dir` must be under `reports/agent_jobs/<job_id>`.
- `check-diff` compares current git changed files against exact
  `allowed_files` entries and writes `diff-check.json` under the task output
  directory when possible.

## Audit Gap

Task cards already cover job-level ownership, allowed files, production-data
access, and diff boundaries, but broader orchestration fields are mostly prose
today:

- Parent goal objective and task-card linkage are not schema-backed.
- Validation expectations and hard stops are documented in Markdown prose.
- Report status artifacts do not share a minimal required summary schema.
- There is no changed-file-scoped helper for validating only the goal/status
  artifacts touched by the current slice.

## This Slice

This slice adds:

- `docs/goals/goal_schema_v1.json` for goal-file frontmatter only.
- `reports/agent_jobs/status_schema_v1.json` for minimal status summaries.
- `scripts/agent_goal_contract.py` for explicit-path or changed-file-scoped
  validation.

It intentionally does not change the existing task-card validator, introduce
merge parking, add Git-ref claims, auto-merge work, or enforce every historical
artifact.
