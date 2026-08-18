---
job_id: control_plane_hook_status_docs_refresh_v1_20260623
lane: Reporting
supporting_lanes:
  - Evaluation
  - Repo Hygiene
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 1800
output_dir: reports/agent_jobs/control_plane_hook_status_docs_refresh_v1_20260623
mutation_mode: safe_extension
production_data_access: false
task_scope: control_plane_only
closeout_scope: docs_report_pr
allowed_files:
  - docs/agent_tasks/control_plane_hook_status_docs_refresh_v1_20260623.md
  - docs/dev_flow/CONTROL_PLANE_OPEN_WORK.md
  - docs/dev_flow/CONTROL_PLANE_STATUS.md
  - reports/agent_jobs/control_plane_hook_status_docs_refresh_v1_20260623/README.md
  - reports/agent_jobs/control_plane_hook_status_docs_refresh_v1_20260623/status.json
  - reports/agent_jobs/control_plane_hook_status_docs_refresh_v1_20260623/validation.md
forbidden_files:
  - financial-engine_v2/data/**
  - financial-engine_v2/reports/**
  - backend/product/runtime source code
  - extraction/parser/evaluator/gold-label/prompt code
  - .github/workflows/**
  - scripts/**
  - .codex/**
  - .claude/**
  - .githooks/**
  - .agents/**
  - AGENTS.md
  - CLAUDE.md
  - DB/Qdrant/news/memory stores
  - source PDFs / ASX docs / production documents
  - secrets, env files, runtime binding files, migrations
---

# Control Plane Hook Status Docs Refresh V1

## Objective

Refresh the current control-plane status docs after PR #399 and PR #400 merged
and after the linked Tenn worktree family was repaired to use local
`core.hooksPath=.githooks`.

Primary lane: Reporting. Supporting lanes: Evaluation and Repo Hygiene.

## Scope

Allowed:

- Update stale hook status wording in `docs/dev_flow/CONTROL_PLANE_OPEN_WORK.md`.
- Update stale hook status wording in `docs/dev_flow/CONTROL_PLANE_STATUS.md`.
- Write this task card and report artifacts for the job.
- Run read-only hook validation commands.

Out of scope:

- Do not mutate Git config, hook scripts, `.githooks`, `.codex`, `.claude`,
  `.agents`, scripts, templates, runtime/product/data/extraction files, CI, or
  production data.
- Do not refresh unrelated `SKILLS_SURFACE.md` freshness metadata.
- Do not merge open PR #402 or edit its guard-script lane.
- Do not backfill task ledger history or normalize unrelated status rows.

## Required Preflight

- Confirm branch, HEAD, worktree path, upstream, remote, status, and recent
  commits.
- Confirm current `origin/migration/clean-runtime-baseline-reconstruct-v1` is
  fetched and records merged PR #399 and PR #400.
- Run portable Tenn git guard preflight.
- Validate this task card.
- Run registry `list-active --read-only` and `check-overlap`.
- Check open PRs for overlap, especially PR #402.
- Confirm strict hook validation currently passes with `core.hooksPath=.githooks`.

## Required Audit

- Search for stale hook-status wording around:
  - `core.hooksPath`
  - `.githooks`
  - `/home/l4nd0/tenn/.git/hooks`
  - `/mnt/sdb2`
  - `common-dir hooks`
  - `Git hook installation check`
- Record each corrected stale claim in the report.

## Required Validation

- Task-card validation.
- Registry `list-active --read-only` and `check-overlap`.
- Strict `scripts/check_agent_hooks.py` for this worktree.
- Strict `scripts/check_agent_hooks.py` for `/home/l4nd0/tenn`.
- Grep/search after edits for the stale hook-path phrases.
- Markdown hygiene if available.
- JSON validation for report artifacts.
- `python3 scripts/agent_job_contract.py check-report-artifacts <task-card>
  --repo-root .`.
- `python3 scripts/agent_job_contract.py check-diff <task-card> --repo-root .
  --no-write-report`.
- `git diff --check`.
- Final changed-files versus `allowed_files`.
- Final `git status --short --untracked-files=all`.

## Definition Of Done

- Current status docs no longer claim that Git hooks are missing because
  `core.hooksPath` points to `/home/l4nd0/tenn/.git/hooks`.
- Docs distinguish current host/local Git config proof from portable repo files.
- No hook implementation or runtime/product/data/extraction behavior changes.
- A focused local commit is ready for PR.
