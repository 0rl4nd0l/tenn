---
job_id: control_plane_sloppy_fix_comment_best_effort_v1_20260607
lane: Evaluation
supporting_lanes:
  - Reporting
  - Repo Hygiene
owner: Codex
allowed_files:
  - .github/workflows/sloppy-fix.yml
  - docs/agent_tasks/control_plane_sloppy_fix_comment_best_effort_v1_20260607.md
  - reports/agent_jobs/control_plane_sloppy_fix_comment_best_effort_v1_20260607/README.md
  - reports/agent_jobs/control_plane_sloppy_fix_comment_best_effort_v1_20260607/validation.json
approval_required: true
timeout_seconds: 900
output_dir: reports/agent_jobs/control_plane_sloppy_fix_comment_best_effort_v1_20260607
mutation_mode: safe_extension
production_data_access: false
---

# Task

Repair the non-critical Sloppy Fix PR comment path after the first live
`workflow_run` activation proved the fix job can run but the comment job failed.

# Scope

Update only `.github/workflows/sloppy-fix.yml` on a clean branch based on live
`origin/main`.

# Required Behavior

- Preserve the existing Sloppy Fix `workflow_run` trigger and same-repository
  gating.
- Preserve the existing Claude provider/auth/model shape.
- Keep Sloppy Fix unscheduled.
- Keep the Sloppy fix job permissions unchanged.
- Give only the separate comment job the permissions needed for PR comments.
- Make PR commenting best-effort so a comment permission failure cannot fail the
  overall Sloppy Fix workflow after the fix job succeeds.

# Hard Boundaries

- Do not edit any workflow other than `.github/workflows/sloppy-fix.yml`.
- Do not edit `.sloppy.yml`.
- Do not change provider, model, or Sloppy action.
- Do not dispatch, rerun, cancel, or delete GitHub Actions.
- Do not touch runtime state, DBs, Qdrant, Redis, news stores, memory stores,
  extraction prompts, parser routing, model/GPU config, backfills, migrations,
  or production data.

# Required Validation

- Validate this task card with available Tenn task-card tooling.
- Task-card `check-diff`.
- YAML parse of `.github/workflows/sloppy-fix.yml`.
- Static check that comment-job `pull-requests: write` exists.
- Static check that PR comment code catches comment failures.
- Static check that no schedule/cron trigger exists.
- `git diff --check`.

# Definition Of Done

- Workflow diff is limited to the comment job.
- PR comment permission/error handling is patched.
- Validation results are recorded in the report.
