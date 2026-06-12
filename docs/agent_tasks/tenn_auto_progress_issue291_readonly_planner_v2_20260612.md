---
job_id: tenn_auto_progress_issue291_readonly_planner_v2_20260612
owner: Codex
lane: Evaluation
supporting_lanes:
  - Repo Hygiene
  - Reporting
status: approved
approval_required: false
allow_unapproved_safe_extension: true
mutation_mode: safe_extension
production_data_access: false
output_dir: reports/agent_jobs/tenn_auto_progress_issue291_readonly_planner_v2_20260612
allowed_files:
  - docs/agent_tasks/tenn_auto_progress_issue291_readonly_planner_v2_20260612.md
  - .agents/skills/tenn-auto-progress/SKILL.md
  - scripts/auto_progress.py
  - reports/agent_jobs/tenn_auto_progress_issue291_readonly_planner_v2_20260612/README.md
  - reports/agent_jobs/tenn_auto_progress_issue291_readonly_planner_v2_20260612/ISSUE_SCAN.md
  - reports/agent_jobs/tenn_auto_progress_issue291_readonly_planner_v2_20260612/MILESTONE_SCAN.md
  - reports/agent_jobs/tenn_auto_progress_issue291_readonly_planner_v2_20260612/CANDIDATE_RANKING.md
  - reports/agent_jobs/tenn_auto_progress_issue291_readonly_planner_v2_20260612/MANDATE_CLASSIFICATION.md
  - reports/agent_jobs/tenn_auto_progress_issue291_readonly_planner_v2_20260612/CONTEXT_PACK.md
  - reports/agent_jobs/tenn_auto_progress_issue291_readonly_planner_v2_20260612/DRAFT_TASK_CARD_ISSUE_234.md
  - reports/agent_jobs/tenn_auto_progress_issue291_readonly_planner_v2_20260612/PHASE3_APPROVAL_MANIFEST.md
  - reports/agent_jobs/tenn_auto_progress_issue291_readonly_planner_v2_20260612/DATA_MISSING.md
  - reports/agent_jobs/tenn_auto_progress_issue291_readonly_planner_v2_20260612/VALIDATION.md
  - reports/agent_jobs/tenn_auto_progress_issue291_readonly_planner_v2_20260612/ISSUES.json
  - reports/agent_jobs/tenn_auto_progress_issue291_readonly_planner_v2_20260612/MILESTONES.json
  - reports/agent_jobs/tenn_auto_progress_issue291_readonly_planner_v2_20260612/ISSUE_234.json
  - reports/agent_jobs/tenn_auto_progress_issue291_readonly_planner_v2_20260612/TRIAGE_RESULT.json
  - reports/agent_jobs/tenn_auto_progress_issue291_readonly_planner_v2_20260612/triage_check/ISSUE_SCAN.md
  - reports/agent_jobs/tenn_auto_progress_issue291_readonly_planner_v2_20260612/triage_check/MILESTONE_SCAN.md
  - reports/agent_jobs/tenn_auto_progress_issue291_readonly_planner_v2_20260612/triage_check/CANDIDATE_RANKING.md
  - reports/agent_jobs/tenn_auto_progress_issue291_readonly_planner_v2_20260612/triage_check/MANDATE_CLASSIFICATION.md
  - reports/agent_jobs/tenn_auto_progress_issue291_readonly_planner_v2_20260612/triage_check/ISSUES.json
  - reports/agent_jobs/tenn_auto_progress_issue291_readonly_planner_v2_20260612/triage_check/MILESTONES.json
  - reports/agent_jobs/tenn_auto_progress_issue291_readonly_planner_v2_20260612/triage_check/TRIAGE_RESULT.json
  - reports/agent_jobs/tenn_auto_progress_issue291_readonly_planner_v2_20260612/issue234_check/CONTEXT_PACK.md
  - reports/agent_jobs/tenn_auto_progress_issue291_readonly_planner_v2_20260612/issue234_check/DRAFT_TASK_CARD_ISSUE_234.md
  - reports/agent_jobs/tenn_auto_progress_issue291_readonly_planner_v2_20260612/issue234_check/PHASE3_APPROVAL_MANIFEST.md
  - reports/agent_jobs/tenn_auto_progress_issue291_readonly_planner_v2_20260612/issue234_check/ISSUE_234.json
timeout_seconds: 7200
---

# Tenn Auto Progress Issue 291 Read-Only Planner V2

## Objective

Make `tenn-auto-progress` reusable for read-only issue/milestone triage and
issue-to-task-card dry runs under issue #291.

## Scope

This is control-plane work only under `REPORT_AUTONOMY` and
`ISSUE_291_READONLY_PLANNER`.

## Allowed Actions

- Inspect issue #291 and current merged `tenn-auto-progress` skill evidence.
- Add or refine a dry-run planner script at `scripts/auto_progress.py`.
- Generate compact report artifacts in the configured `output_dir`.
- Draft an issue-to-task-card packet for the selected top candidate as report
  text only.
- Run read-only GitHub commands.
- Run task-card validation, script syntax checks, script dry runs, markdown
  whitespace checks, `git diff --check`, and changed-path guards.

## Forbidden Actions

- Do not touch
  `docs/agent_tasks/extraction_count24_approval_packet_current_canonical_v1_20260609.md`.
- Do not mutate product, backend, frontend, runtime, extraction, data, prompt,
  source-PDF, gold-label, DB, Qdrant, news, memory, service, model, GPU,
  backfill, production-data, or live-service files.
- Do not run extraction work, product/runtime/extraction validation, service
  starts, dependency installs, or broad validation.
- Do not create a real task card for the candidate issue.
- Do not execute a candidate issue.
- Do not commit, push, merge, rebase, cherry-pick, reset, stash, clean, delete
  branches, remove worktrees, or mutate GitHub.

Later explicit preservation approval may commit these exact V2 control-plane
artifacts, push this branch, and open a PR. That approval does not authorize
candidate execution, #234 work, broad validation, destructive Git operations,
or product/runtime/data/extraction mutation.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/tenn_auto_progress_issue291_readonly_planner_v2_20260612.md`
- `python3 -m py_compile scripts/auto_progress.py`
- `python3 scripts/auto_progress.py triage-issues --repo 0rl4nd0l/tenn --milestone "M0 — Control Plane Hardening" --labels state:ready --risk low,medium --max-candidates 10 --output-dir reports/agent_jobs/tenn_auto_progress_issue291_readonly_planner_v2_20260612 --dry-run`
- `python3 scripts/auto_progress.py issue-to-card --repo 0rl4nd0l/tenn --issue 234 --output-dir reports/agent_jobs/tenn_auto_progress_issue291_readonly_planner_v2_20260612 --dry-run`
- `python3 scripts/auto_progress.py triage-issues --repo 0rl4nd0l/tenn --milestone "M0 — Control Plane Hardening" --labels state:ready --risk low,medium --output-dir reports/agent_jobs/tenn_auto_progress_issue291_readonly_planner_v2_20260612/triage_check --dry-run`
- `python3 scripts/auto_progress.py issue-to-card --repo 0rl4nd0l/tenn --issue 234 --output-dir reports/agent_jobs/tenn_auto_progress_issue291_readonly_planner_v2_20260612/issue234_check --dry-run`
- Required files exist.
- Markdown whitespace check.
- `git diff --check`.
- Changed-path guard proving no product/runtime/data/extraction paths changed.
- Final `git status --short --untracked-files=all`.
