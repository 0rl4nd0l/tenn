---
job_id: sloppy_automation_scan_artifact_repair_v1_20260629
lane: Reporting
supporting_lanes:
  - Evaluation
  - Repo Hygiene
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 1800
output_dir: reports/agent_jobs/sloppy_automation_scan_artifact_repair_v1_20260629
mutation_mode: safe_extension
production_data_access: false
task_scope: control_plane_only
closeout_scope: control_plane_only
allowed_files:
  - docs/agent_tasks/sloppy_automation_scan_artifact_repair_v1_20260629.md
  - .sloppy.yml
  - .github/workflows/sloppy-scan.yml
  - .github/workflows/sloppy-fix.yml
  - reports/agent_jobs/sloppy_automation_scan_artifact_repair_v1_20260629/STATE.md
  - reports/agent_jobs/sloppy_automation_scan_artifact_repair_v1_20260629/DECISIONS.md
  - reports/agent_jobs/sloppy_automation_scan_artifact_repair_v1_20260629/VALIDATION.md
  - reports/agent_jobs/sloppy_automation_scan_artifact_repair_v1_20260629/DOCS_IMPACT.md
  - reports/agent_jobs/sloppy_automation_scan_artifact_repair_v1_20260629/PR_REVIEW.md
  - reports/agent_jobs/sloppy_automation_scan_artifact_repair_v1_20260629/NEXT_GOAL.md
  - reports/agent_jobs/sloppy_automation_scan_artifact_repair_v1_20260629/TASK_LEDGER_ENTRY.json
forbidden_files:
  - AGENTS.md
  - CLAUDE.md
  - financial-engine_v2/**
  - scripts/**
  - .agents/**
  - .codex/**
  - .claude/**
  - .githooks/**
  - runtime/product/data/extraction/parser/evaluator/gold-label/prompt paths
  - DB/Qdrant/Redis/news/memory stores
  - secrets, env files, runtime binding files, service files, migrations
---

# Sloppy Automation Scan Artifact Repair V1

## Objective

Repair the GitHub Sloppy automation chain so Sloppy Scan produces a usable
issues artifact for Sloppy Fix, and so branch-local workflow/config files match
the currently proven default-branch Sloppy Fix trigger shape.

## Evidence

Read-only GitHub inspection on 2026-06-29 showed:

- Sloppy Scan run `28355506916` completed with local issues but used model text
  `openai/gpt-4o-mini  # model for free scan tier`, made zero API calls, and
  produced no downloadable `sloppy-scan-issues` artifact.
- Sloppy Fix run `28355563360` started from `workflow_run`, detected Claude
  credentials, then skipped because the scan artifact was missing.
- Remote default-branch Sloppy Fix uses `workflow_dispatch` plus `workflow_run`
  after Sloppy Scan, Claude credentials, PR comments, and fail-closed handling.
- The canonical migration branch still has the older scheduled/manual Sloppy
  Fix and lacks scan artifact upload.

## Scope

Allowed:

- Normalize `.sloppy.yml` so action-consumed values do not include inline
  explanatory comments or duplicate top-level keys.
- Make Sloppy Scan write and upload `/tmp/sloppy-scan-issues.json`.
- Make Sloppy Fix match the default-branch workflow-run Claude/comment
  behavior.
- Preserve report-local validation and closeout artifacts.

Out of scope:

- Do not run write-capable GitHub workflows.
- Do not push, open a PR, commit, merge, rebase, reset, stash, clean, prune, or
  delete branches/worktrees unless explicitly requested after validation.
- Do not mutate host-local systemd timers, Codex hooks, secrets, runtime state,
  product code, data stores, extraction code, source PDFs, prompts, labels, or
  service config.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/sloppy_automation_scan_artifact_repair_v1_20260629.md`
- Portable Tenn git guard preflight for this task worktree.
- `python3 scripts/tenn_dev_status.py`
- YAML parse for `.sloppy.yml` and both Sloppy workflow files.
- Focused config sanity check that Sloppy model/output values are comment-free
  and non-empty where required.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/sloppy_automation_scan_artifact_repair_v1_20260629.md --repo-root . --no-write-report`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/sloppy_automation_scan_artifact_repair_v1_20260629.md --repo-root .`
- Final `git status --short --untracked-files=all`.

## Definition Of Done

- Local config/workflow validation passes.
- The scan workflow has an explicit output path and upload artifact step.
- The fix workflow is workflow-run capable and Claude-backed.
- No forbidden files are changed.
- Runtime/GitHub automation functionality is not claimed as `WORKING` until a
  pushed branch produces a fresh successful Sloppy Scan artifact and Sloppy Fix
  consumes it.
