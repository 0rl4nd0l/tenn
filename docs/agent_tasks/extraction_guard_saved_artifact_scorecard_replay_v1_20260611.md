---
job_id: extraction_guard_saved_artifact_scorecard_replay_v1_20260611
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_guard_saved_artifact_scorecard_replay_v1_20260611.md
  - reports/agent_jobs/extraction_guard_saved_artifact_scorecard_replay_v1_20260611/README.md
  - reports/agent_jobs/extraction_guard_saved_artifact_scorecard_replay_v1_20260611/status.json
  - reports/agent_jobs/extraction_guard_saved_artifact_scorecard_replay_v1_20260611/live_git_status.json
  - reports/agent_jobs/extraction_guard_saved_artifact_scorecard_replay_v1_20260611/guard_scorecard_replay.json
  - reports/agent_jobs/extraction_guard_saved_artifact_scorecard_replay_v1_20260611/validation.json
  - reports/agent_jobs/extraction_guard_saved_artifact_scorecard_replay_v1_20260611/diff-check.json
approval_required: false
allow_audit_code_changes: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_guard_saved_artifact_scorecard_replay_v1_20260611
mutation_mode: audit_only
production_data_access: false
github_mutation_allowed: false
---

# Guard Saved-Artifact Scorecard Replay

## Objective

Build a report-only guard packet from saved artifacts for WHC plus the current
CTN, HUB, AZJ, and NSR guard cases before any merge or push decision.

## Scope

- Use saved artifacts only.
- Do not run extraction, count samples, broad replay, backfill, service routes,
  or production persistence.
- Do not change code; this is report-only work expressed as validator-supported
  `audit_only` mode.
- Do not use count-24/count-32 or PR #318 patch sources.

## Required Guard Cases

- WHC `9640d9f1-a45b-492d-8df5-9bad0f46431c`
- CTN `dec0b5f1-e6d2-48d8-ad9d-16ffd540ee39`
- HUB `419bcca8-213e-4706-8962-8e3bd8adf091`
- LBL `551c6b84-1053-405c-a833-4ecc018e2045` as the HUB negative guard
- AZJ `488d6f1a-0180-4fca-8dcf-c4cdfc0f342e`
- NSR `f2240712-9dde-41e0-88fa-29c1a0080dab`

## Validation

- Task-card validate.
- Registry `list-active --read-only`.
- JSON validation for report artifacts.
- `git diff --check`.
- Task-card `check-diff`.
- Forbidden-surface path audit.

## Final Report

Report the branch, HEAD, worktree, registry state, saved-artifact inputs, guard
case outcomes, observed gains, negative controls, `DATA_MISSING`, forbidden
actions not run, and the next recommended step.
