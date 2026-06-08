---
job_id: control_plane_sloppy_fix_provider_failclosed_v1_20260607
lane: Evaluation
supporting_lanes:
  - Reporting
  - Repo Hygiene
owner: Codex
allowed_files:
  - .github/workflows/sloppy-fix.yml
  - scripts/test_sloppy_fix_workflow.py
  - docs/agent_tasks/control_plane_sloppy_fix_provider_failclosed_v1_20260607.md
  - reports/agent_jobs/control_plane_sloppy_fix_provider_failclosed_v1_20260607/README.md
  - reports/agent_jobs/control_plane_sloppy_fix_provider_failclosed_v1_20260607/validation.json
  - reports/agent_jobs/control_plane_sloppy_fix_provider_failclosed_v1_20260607/diff-check.json
  - plan.html
approval_required: true
timeout_seconds: 1800
output_dir: reports/agent_jobs/control_plane_sloppy_fix_provider_failclosed_v1_20260607
mutation_mode: safe_extension
production_data_access: false
---

# Task

Patch Sloppy Fix so a seeded Sloppy Scan with found issues cannot finish green
when Sloppy Fix fixes zero issues.

# Scope

Update only the Sloppy Fix GitHub Actions workflow behavior and focused static
workflow tests on a clean branch based on live `origin/main`.

# Required Behavior

- Preserve Sloppy Fix `workflow_dispatch` and completed `Sloppy Scan`
  `workflow_run` triggers.
- Keep Sloppy Fix unscheduled.
- Preserve same-repository gating for automatic runs.
- Preserve the existing Claude provider/auth/model shape.
- Preserve artifact handoff when the triggering scan uploaded
  `sloppy-scan-issues`.
- Preserve the existing skip-success behavior for missing scan artifacts.
- Preserve skip-success behavior when the scan artifact reports zero found
  issues.
- Preserve manual `workflow_dispatch` fallback behavior.
- Keep malformed artifact JSON as a hard error.
- For automatic `workflow_run` attempts with a positive seeded found count,
  fail closed when Sloppy Fix reports zero fixed issues or an invalid fixed
  issue count.
- Keep PR commenting best-effort and make zero-fix failure status visible.

# Hard Boundaries

- Do not edit `.github/workflows/sloppy-scan.yml`.
- Do not edit `.sloppy.yml`.
- Do not change Sloppy action source, provider, model, or credential names.
- Do not add schedule/cron triggers.
- Do not touch runtime state, DBs, Qdrant, Redis, news stores, memory stores,
  source PDFs, gold labels, extraction prompts, parser routing, model/GPU
  config, backfills, migrations, or production data.
- Do not push, dispatch GitHub Actions, merge PRs, or edit GitHub issues
  without explicit approval.
- Do not merge the disposable proof PR #307.

# Required Validation

- Validate this task card with available Tenn task-card tooling from the sibling
  agent-contract worktree.
- Use TDD:
  - RED: add a focused workflow behavior test proving seeded zero-fix runs fail
    closed, and run it before implementation.
  - GREEN: patch the workflow and rerun the focused test.
  - REFACTOR: add focused static assertions for preserved provider selection,
    seeded count propagation, and no schedule/cron trigger.
- YAML parse of `.github/workflows/sloppy-fix.yml`.
- Static check that Sloppy Fix still uses Claude provider/auth/model.
- Static check that seeded issue count propagates from the selector step to the
  comment job.
- Static check that automatic seeded positive issue runs fail when the action
  reports zero or invalid fixed issue count.
- Static check that no schedule/cron trigger exists.
- `git diff --check`.
- Task-card `check-diff` using the sibling agent-contract validator.

# Definition Of Done

- Workflow diff is limited to `.github/workflows/sloppy-fix.yml`.
- Focused tests are present and pass.
- Task card and report artifacts are present.
- Validation results are recorded in the report.
- Live GitHub Actions rerun evidence remains `DATA_MISSING` unless the user
  explicitly approves push/dispatch.
