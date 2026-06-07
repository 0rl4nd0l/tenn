---
job_id: control_plane_sloppy_fix_default_branch_auto_v1_20260607
lane: Evaluation
supporting_lanes:
  - Reporting
  - Repo Hygiene
owner: Codex
allowed_files:
  - .github/workflows/sloppy-fix.yml
  - docs/agent_tasks/control_plane_sloppy_fix_default_branch_auto_v1_20260607.md
  - reports/agent_jobs/control_plane_sloppy_fix_default_branch_auto_v1_20260607/README.md
  - reports/agent_jobs/control_plane_sloppy_fix_default_branch_auto_v1_20260607/validation.json
approval_required: true
timeout_seconds: 1800
output_dir: reports/agent_jobs/control_plane_sloppy_fix_default_branch_auto_v1_20260607
mutation_mode: safe_extension
production_data_access: false
---

# Task

Implement the P0 Sloppy Fix automatic post-scan workflow fix on the GitHub
default branch surface.

# Scope

Update only `.github/workflows/sloppy-fix.yml` on a clean branch based on live
`origin/main`. GitHub `workflow_run` triggers only activate when the workflow
file exists on the default branch, so this task intentionally targets `main`
rather than `migration/clean-runtime-baseline-reconstruct-v1`.

# Required Behavior

- Keep `workflow_dispatch`.
- Keep Sloppy Fix unscheduled.
- Preserve the existing Claude provider/auth shape.
- Add `workflow_run` for completed `Sloppy Scan` runs.
- Run only when the upstream Sloppy Scan conclusion is `success`.
- Run only when the upstream head repository is the same repository.
- Avoid direct `secrets.*` references in step-level `if:` expressions.
- Keep shell credential detection.
- Add PR commenting for automatic post-scan runs when a PR is present.

# Hard Boundaries

- Do not push.
- Do not create, edit, close, label, reopen, or comment on GitHub issues or PRs.
- Do not dispatch, cancel, delete, or rerun GitHub Actions.
- Do not edit crontab, systemd units, symlinks, local timers, or host runtime
  config.
- Do not touch product runtime, DBs, Qdrant, Redis, news stores, memory stores,
  source PDFs, gold labels, extraction prompts, parser routing, model/GPU
  config, backfills, migrations, or production data.
- Do not edit any workflow other than `.github/workflows/sloppy-fix.yml`.
- Do not edit `.sloppy.yml`.
- Do not change provider/model/action unless required to preserve existing
  default-branch behavior.

# Required Validation

- Validate this task card with available Tenn task-card tooling, if available
  from a sibling current-origin checkout.
- YAML parse of `.github/workflows/sloppy-fix.yml`.
- Static check that the workflow contains `workflow_run`, `Sloppy Scan`, and
  same-repository gating.
- Static check that no schedule/cron trigger was reintroduced.
- `git diff --check`
- Task-card `check-diff` with available Tenn task-card tooling, if available
  from a sibling current-origin checkout.

# Definition Of Done

- Workflow diff is limited to `.github/workflows/sloppy-fix.yml`.
- Task card and report artifacts are present.
- Validation results are recorded in the report.
- Remaining live GitHub proof is clearly marked `DATA_MISSING` because this
  task does not push or dispatch workflows.
