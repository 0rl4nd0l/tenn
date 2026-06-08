---
job_id: control_plane_sloppy_fix_live_proof_v1_20260608
lane: Evaluation
supporting_lanes:
  - Reporting
  - Repo Hygiene
owner: Codex
allowed_files:
  - .github/workflows/sloppy-fix.yml
  - scripts/test_sloppy_fix_workflow.py
  - docs/agent_tasks/control_plane_sloppy_fix_provider_failclosed_v1_20260607.md
  - docs/agent_tasks/control_plane_sloppy_fix_live_proof_v1_20260608.md
  - reports/agent_jobs/control_plane_sloppy_fix_provider_failclosed_v1_20260607/README.md
  - reports/agent_jobs/control_plane_sloppy_fix_provider_failclosed_v1_20260607/validation.json
  - reports/agent_jobs/control_plane_sloppy_fix_provider_failclosed_v1_20260607/diff-check.json
  - reports/agent_jobs/control_plane_sloppy_fix_live_proof_v1_20260608/README.md
  - reports/agent_jobs/control_plane_sloppy_fix_live_proof_v1_20260608/validation.json
  - reports/agent_jobs/control_plane_sloppy_fix_live_proof_v1_20260608/diff-check.json
  - plan.html
approval_required: true
timeout_seconds: 1800
output_dir: reports/agent_jobs/control_plane_sloppy_fix_live_proof_v1_20260608
mutation_mode: report_only
production_data_access: false
---

# Task

Prepare the approval-gated live Sloppy Fix proof for milestone 3 in
`plan.html`.

# Scope

This task is report-only until the user explicitly approves GitHub write
actions. It may refresh read-only GitHub evidence, inspect existing Sloppy Scan
and Sloppy Fix runs, and write a report/approval packet. It does not authorize
pushes, workflow dispatches, branch mutations, PR mutations, or issue edits.

# Required Behavior

- Preserve the dirty shared checkout.
- Use the local milestone-2 branch as the candidate patch source.
- Verify the known issue-bearing proof PR and prior Sloppy run evidence
  read-only.
- Identify the exact live proof command sequence that would be run after
  approval.
- Stop in `WAITING_ON_USER` before any GitHub write.

# Hard Boundaries

- Do not push branches.
- Do not dispatch or rerun GitHub Actions.
- Do not merge, rebase, reset, clean, prune, or delete branches/worktrees.
- Do not comment on, close, reopen, label, or edit GitHub issues or PRs.
- Do not merge disposable PR #307.
- Do not touch runtime state, DBs, Qdrant, Redis, news stores, source PDFs, gold
  labels, extraction prompts, parser routing, model/GPU config, backfills, or
  production data.

# Required Validation

- Validate this task card with available Tenn task-card tooling.
- Refresh PR #307 state read-only.
- Refresh prior Sloppy Scan/Fix run state read-only.
- Prove the prior scan artifact contains seeded found issues.
- Prove the prior fix run fixed zero and still succeeded.
- Write the exact `WAITING_ON_USER` block to the report.
- `git diff --check`.
- Task-card `check-diff` with available Tenn task-card tooling.

# Definition Of Done

- Approval packet is present under `reports/agent_jobs/...`.
- It includes exact evidence, exact blocked approval, and exact next commands.
- No GitHub writes or runtime/data mutations occurred.
