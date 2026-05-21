---
job_id: sloppy_fix_manual_only_v1
lane: Evaluation
owner: Codex
allowed_files:
  - .github/workflows/sloppy-fix.yml
  - docs/agent_tasks/sloppy_fix_manual_only_v1.md
  - reports/agent_jobs/sloppy_fix_manual_only_v1/**
approval_required: true
timeout_seconds: 1800
output_dir: reports/agent_jobs/sloppy_fix_manual_only_v1
mutation_mode: safe_extension
production_data_access: false
---

# Task

Make the scheduled Sloppy Fix GitHub Actions workflow manual-only.

# Background

The prior audit `sloppy_fix_ownership_audit_v1` found:

- `.github/workflows/sloppy-fix.yml` is scheduled and manual.
- It declares `contents: write` and `pull-requests: write`.
- It runs `braedonsaunders/sloppy@main` in `mode: fix` with `agent: codex`.
- It uses `OPENAI_API_KEY`.
- It has no Tenn task-card or registry relationship.
- It is outside the local report-only `tenn-codex-*` timer model.
- Recommended treatment: make manual-only later under explicit approval.

# Required change

Modify only `.github/workflows/sloppy-fix.yml` so that:

1. `workflow_dispatch` remains available.
2. The scheduled cron trigger is removed.
3. Add a short YAML comment near the trigger explaining:
   - Sloppy Fix is operator-triggered only.
   - It must not be scheduled without explicit Tenn approval because it is a write-capable automation outside task-card/registry discipline.

Do not change provider, model, permissions, secrets, Sloppy mode, action versions, branch behavior, `.sloppy.yml`, or any other workflow in this task.

# Hard boundaries

Do not edit code outside `.github/workflows/sloppy-fix.yml`.
Do not edit `.github/workflows/sloppy-scan.yml`, `.github/workflows/claude.yml`, `.github/workflows/codeql.yml`, `.github/workflows/ci.yml`, `.github/dependabot.yml`, `.sloppy.yml`, systemd files, Codex automation runner files, or local timer files.
Do not enable, disable, rerun, cancel, delete, or reschedule GitHub Actions through GitHub.
Do not push.
Do not create, update, close, or merge PRs.
Do not mutate production data.
Do not touch DBs, Qdrant, news.sqlite, embeddings, company memory, market memory, thesis memory, financial truth, parser routing, gold labels, extraction prompts, runtime bindings, migrations, ingestion, sync, reindexing, or backfills.
Do not use Chrome/browser automation.
Do not pin actions or permission-reduce in this task; those are separate future hardening tasks.

# Required preflight

1. Print current worktree path.
2. Print branch and HEAD.
3. Run `git status --short --untracked-files=all`.
4. Run `git worktree list`.
5. Run recent commits summary.
6. Validate this task card if repo tooling supports validation.
7. Run registry/list-active if available.
8. Run registry/check-overlap for this task card if available.
9. Claim the task if registry supports it and it is safe.
10. If current worktree has unrelated dirty files, prefer a clean isolated worktree/branch before editing. If isolation is not possible and check-overlap is not clean for `.github/workflows/sloppy-fix.yml`, stop and report.

# Implementation requirements

Change `.github/workflows/sloppy-fix.yml` only.

Expected trigger shape after change should be manual-only, for example:

```yaml
on:
  workflow_dispatch:
```
