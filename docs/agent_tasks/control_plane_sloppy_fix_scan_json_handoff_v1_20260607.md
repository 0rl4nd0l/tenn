---
job_id: control_plane_sloppy_fix_scan_json_handoff_v1_20260607
lane: Evaluation
supporting_lanes:
  - Reporting
  - Repo Hygiene
owner: Codex
allowed_files:
  - .github/workflows/sloppy-scan.yml
  - .github/workflows/sloppy-fix.yml
  - docs/agent_tasks/control_plane_sloppy_fix_scan_json_handoff_v1_20260607.md
  - reports/agent_jobs/control_plane_sloppy_fix_scan_json_handoff_v1_20260607/README.md
  - reports/agent_jobs/control_plane_sloppy_fix_scan_json_handoff_v1_20260607/validation.json
approval_required: true
timeout_seconds: 1800
output_dir: reports/agent_jobs/control_plane_sloppy_fix_scan_json_handoff_v1_20260607
mutation_mode: safe_extension
production_data_access: false
---

# Task

Make automatic Sloppy Fix consume Sloppy Scan findings from the triggering
workflow run, so a scan that reports issues does not depend on an independent
fix-mode rescan.

# Scope

Update only the Sloppy GitHub Actions workflow handoff on a clean branch based on
live `origin/main`.

# Required Behavior

- Preserve Sloppy Scan `pull_request` and `workflow_dispatch` triggers.
- Preserve Sloppy Fix `workflow_dispatch` and completed `Sloppy Scan`
  `workflow_run` triggers.
- Keep Sloppy Fix unscheduled.
- Preserve the existing Sloppy Scan provider defaults and Codex compatibility
  shim.
- Preserve the existing Sloppy Fix Claude provider/auth/model shape.
- Have Sloppy Scan write issues JSON with Sloppy's `output-file` input.
- Upload the scan issues JSON as a required workflow artifact after successful
  scans.
- Have Sloppy Fix download the triggering Sloppy Scan artifact when run by
  `workflow_run`.
- Fail automatic `workflow_run` fix attempts closed when the scan issues artifact
  is missing or malformed.
- Pass the downloaded issues JSON back to Sloppy Fix through `output-file`.
- Keep the fallback temp `output-file` path only for manual `workflow_dispatch`.
- Pin automatic Sloppy Fix checkout to the triggering scan `head_sha` so scan
  issues match the checked-out tree.
- Skip Sloppy Fix on automatic runs when the triggering scan artifact contains
  zero found issues.
- Keep same-repository gating for automatic Sloppy Fix runs.
- Keep PR commenting best-effort.

# Hard Boundaries

- Do not edit `.sloppy.yml`.
- Do not change the Sloppy action source or pin.
- Do not change Sloppy Fix provider, model, or credential names.
- Do not add schedule/cron triggers.
- Do not touch runtime state, DBs, Qdrant, Redis, news stores, memory stores,
  source PDFs, gold labels, extraction prompts, parser routing, model/GPU
  config, backfills, migrations, or production data.
- Do not edit GitHub issues.
- Do not merge the disposable proof PR #307.

# Required Validation

- Validate this task card with available Tenn task-card tooling, if available
  from a sibling current-origin checkout.
- YAML parse of `.github/workflows/sloppy-scan.yml` and
  `.github/workflows/sloppy-fix.yml`.
- Static check that Sloppy Scan sets `output-file`.
- Static check that Sloppy Scan uploads a `sloppy-scan-issues` artifact.
- Static check that Sloppy Fix downloads the triggering run artifact with
  `run-id: ${{ github.event.workflow_run.id }}`.
- Static check that Sloppy Fix passes the selected issues path as `output-file`.
- Static check that automatic Sloppy Fix validates scan artifact JSON before
  invoking fix mode.
- Static check that automatic Sloppy Fix checkout uses the triggering
  `head_sha`.
- Static check that no schedule/cron trigger exists in either workflow.
- `git diff --check`.
- Task-card `check-diff` with available Tenn task-card tooling, if available
  from a sibling current-origin checkout.

# Definition Of Done

- Workflow diff is limited to the scan/fix handoff.
- Task card and report artifacts are present.
- Validation results are recorded in the report.
- Live rerun evidence against disposable PR #307 is recorded after the workflow
  reaches the default branch.
