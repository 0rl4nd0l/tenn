---
job_id: extraction_issue286_closeout_after_pr364_v1_20260617
lane: Reporting
supporting_lanes:
  - Financial Truth
  - Provenance
  - Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_issue286_closeout_after_pr364_v1_20260617.md
  - reports/agent_jobs/extraction_issue286_closeout_after_pr364_v1_20260617/README.md
  - reports/agent_jobs/extraction_issue286_closeout_after_pr364_v1_20260617/resolution_review.md
  - reports/agent_jobs/extraction_issue286_closeout_after_pr364_v1_20260617/issue_comment.md
  - reports/agent_jobs/extraction_issue286_closeout_after_pr364_v1_20260617/status.json
  - reports/agent_jobs/extraction_issue286_closeout_after_pr364_v1_20260617/diff-check.json
approval_required: true
allow_unapproved_safe_extension: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_issue286_closeout_after_pr364_v1_20260617
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
github_mutation_allowed: true
---

# Issue 286 Closeout After PR 364

## Objective

Review issue #286 after merged PR #364. If all issue acceptance criteria are
satisfied, add a concise closeout comment and close the GitHub issue. If any
acceptance criterion remains incomplete, leave the issue open and report the
exact remaining blocker.

## Allowed GitHub Mutations

- Add one closeout comment to issue #286 if the resolution review returns
  `PASS_CLOSEOUT`.
- Close issue #286 if the resolution review returns `PASS_CLOSEOUT`.

## Hard Stops

- Do not touch count-24.
- Do not run count-24, count-32, broad extraction, or backfill.
- Do not mutate product/runtime/data/extraction files.
- Do not mutate live DB, Qdrant, Redis, news, memory, source PDFs, gold labels,
  prompts, runtime state, model/GPU/service config, or production data.
- Do not clean, reset, stash, delete branches, or remove worktrees.
- Do not start new extraction implementation.

## Required Evidence

- Fetch `origin/migration/clean-runtime-baseline-reconstruct-v1`.
- Verify PR #364 is merged and canonical contains merge commit
  `f6b8a606d391f7e040aa97746098a981edb49841`.
- Read issue #286.
- Review merged evidence for accounting parsing, payload `field_provenance`,
  consumers preferring field provenance, persisted `metric_provenance`, and
  validation from PR #364.
- Run read-only registry and task-ledger preflight.
