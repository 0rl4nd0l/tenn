---
job_id: extraction_lbl_saved_artifact_scorecard_pr362_v1_20260616
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Repo Hygiene
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_lbl_saved_artifact_scorecard_pr362_v1_20260616.md
  - reports/agent_jobs/extraction_lbl_saved_artifact_scorecard_pr362_v1_20260616/README.md
  - reports/agent_jobs/extraction_lbl_saved_artifact_scorecard_pr362_v1_20260616/status.json
  - reports/agent_jobs/extraction_lbl_saved_artifact_scorecard_pr362_v1_20260616/pr_snapshot.json
  - reports/agent_jobs/extraction_lbl_saved_artifact_scorecard_pr362_v1_20260616/saved_artifact_scorecard.json
  - reports/agent_jobs/extraction_lbl_saved_artifact_scorecard_pr362_v1_20260616/readiness_decision.json
  - reports/agent_jobs/extraction_lbl_saved_artifact_scorecard_pr362_v1_20260616/validation.json
  - reports/agent_jobs/extraction_lbl_saved_artifact_scorecard_pr362_v1_20260616/diff-check.json
approval_required: false
allow_audit_code_changes: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_lbl_saved_artifact_scorecard_pr362_v1_20260616
mutation_mode: audit_only
production_data_access: false
github_mutation_allowed: false
---

# LBL Saved-Artifact Scorecard For PR 362

## Objective

Run a report-only current saved-artifact scorecard for PR #362 after the bounded
LBL row-ref repair and decide whether the PR can move from draft to
ready-for-review/merge, needs one more focused repair, or needs a count-24
approval packet refresh.

## Scope

- Use saved report artifacts and live read-only GitHub/registry state only.
- Compare the prior guard saved-artifact LBL fail-closed row with the repaired
  LBL replay artifact on the PR branch.
- Preserve the existing WHC, CTN, HUB, AZJ, and NSR saved-artifact guard
  conclusions from the prior scorecard packet as current contextual guards, not
  as fresh extraction runs.
- Do not change code.

## Hard Stops

- Do not run count-24, count-32, random samples, broad extraction, backfills, or
  canonical writes.
- Do not mutate DB, Qdrant, Redis, news, memory, source PDFs, prompts, gold
  labels, schema, runtime/model/GPU config, or production data.
- Do not merge PR #362 and do not use PR #318.

## Validation

- Task-card validate.
- Registry `list-active --read-only`.
- Live PR #362 snapshot.
- JSON validation for saved-artifact inputs and report artifacts.
- Saved-artifact assertions for LBL replay status, source-bound period, scale,
  currency, non-null metric count, and repaired target row refs.
- `git diff --check`.
- Task-card `check-diff`.
- Forbidden-surface path audit via changed path inspection only.

## Decision Contract

Return exactly one primary decision:

- `READY_FOR_REVIEW_MERGE`: PR #362 can move from draft to ready-for-review and
  merge consideration.
- `NEEDS_FOCUSED_REPAIR`: one more bounded repair is required before review.
- `NEEDS_COUNT24_APPROVAL_REFRESH`: saved-artifact evidence is good enough that
  the next meaningful gate is an explicit count-24 approval packet refresh.
- `BLOCKED`: required saved-artifact evidence is unavailable or contradictory.
