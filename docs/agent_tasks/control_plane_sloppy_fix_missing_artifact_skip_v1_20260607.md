---
job_id: control_plane_sloppy_fix_missing_artifact_skip_v1_20260607
lane: Evaluation
supporting_lanes:
  - Reporting
  - Repo Hygiene
owner: Codex
allowed_files:
  - .github/workflows/sloppy-fix.yml
  - docs/agent_tasks/control_plane_sloppy_fix_missing_artifact_skip_v1_20260607.md
  - reports/agent_jobs/control_plane_sloppy_fix_missing_artifact_skip_v1_20260607/README.md
  - reports/agent_jobs/control_plane_sloppy_fix_missing_artifact_skip_v1_20260607/validation.json
approval_required: true
timeout_seconds: 900
output_dir: reports/agent_jobs/control_plane_sloppy_fix_missing_artifact_skip_v1_20260607
mutation_mode: safe_extension
production_data_access: false
---

# Task

Repair the Sloppy Fix missing-artifact behavior after the scan JSON handoff
change made automatic fix runs fail when a triggering scan did not upload
`sloppy-scan-issues`.

# Scope

Update only `.github/workflows/sloppy-fix.yml` on a clean branch based on live
`origin/main`.

# Required Behavior

- Preserve Sloppy Fix `workflow_dispatch` and completed `Sloppy Scan`
  `workflow_run` triggers.
- Keep Sloppy Fix unscheduled.
- Preserve same-repository gating for automatic runs.
- Preserve the existing Claude provider/auth/model shape.
- Preserve artifact handoff when the triggering scan uploaded
  `sloppy-scan-issues`.
- Do not fall back to independent rescan on automatic runs when the scan artifact
  is missing.
- Skip fix mode successfully on automatic runs when the scan artifact is missing.
- Keep manual `workflow_dispatch` fallback behavior unchanged.
- Keep malformed artifact JSON as a hard error.
- Keep PR commenting best-effort and make the missing-artifact skip visible.

# Hard Boundaries

- Do not edit `.github/workflows/sloppy-scan.yml`.
- Do not edit `.sloppy.yml`.
- Do not change Sloppy action source, provider, model, or credential names.
- Do not add schedule/cron triggers.
- Do not touch runtime state, DBs, Qdrant, Redis, news stores, memory stores,
  source PDFs, gold labels, extraction prompts, parser routing, model/GPU
  config, backfills, migrations, or production data.
- Do not edit GitHub issues.
- Do not merge the disposable proof PR #307.

# Required Validation

- Validate this task card with available Tenn task-card tooling, if available
  from a sibling current-origin checkout.
- YAML parse of `.github/workflows/sloppy-fix.yml`.
- Static check that artifact download is best-effort.
- Static check that automatic missing-artifact runs skip Sloppy fix mode.
- Static check that automatic missing-artifact runs do not pass a fallback
  `output-file` to Sloppy fix mode.
- Static check that malformed artifact JSON still fails.
- Static check that no schedule/cron trigger exists.
- `git diff --check`.
- Task-card `check-diff` with available Tenn task-card tooling, if available
  from a sibling current-origin checkout.

# Definition Of Done

- Workflow diff is limited to `.github/workflows/sloppy-fix.yml`.
- Task card and report artifacts are present.
- Validation results are recorded in the report.
- Live evidence records the proof handoff run and the unrelated missing-artifact
  failure that this patch addresses.
