---
job_id: issue234_closeout_v1_20260626
owner: Codex
lane: Reporting
supporting_lanes:
  - Repo Hygiene
status: approved
approval_required: false
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
closeout_scope: report_only
output_dir: reports/agent_jobs/issue234_closeout_v1_20260626
allowed_files:
  - docs/agent_tasks/issue234_closeout_v1_20260626.md
  - reports/agent_jobs/issue234_closeout_v1_20260626/README.md
  - reports/agent_jobs/issue234_closeout_v1_20260626/status.json
  - reports/agent_jobs/issue234_closeout_v1_20260626/issue_closeout_matrix.md
  - reports/agent_jobs/issue234_closeout_v1_20260626/followup_issue_map.md
  - reports/agent_jobs/issue234_closeout_v1_20260626/data_missing.md
  - reports/agent_jobs/issue234_closeout_v1_20260626/github_closeout_comment.md
timeout_seconds: 1800
---

# Issue 234 Closeout

## Objective

Close GitHub issue #234,
`[Repo Hygiene] Classify stale extraction contract parity diff-check dirt`, as
superseded after the issue #234 classification packet was preserved through
merged PR #411.

## Scope

Scope: `report_only`

This task may read live Git, PR #411, issue #234, task-card validation, and the
preserved issue #234 report packet. It may write only this task card and the
report files listed in `allowed_files`.

## GitHub Mutation Contract

Allowed GitHub mutations:

- Add one closeout comment to issue #234.
- Close issue #234.
- After the operator's 2026-06-26 `proceed`, push this exact closeout-report
  branch, open a PR targeting
  `migration/clean-runtime-baseline-reconstruct-v1`, and merge that PR only if
  the staged diff remains limited to `allowed_files`, local validation remains
  clean, code review has no findings, and live GitHub checks are green.
- If canonical advances before the closeout-report PR is opened, perform one
  non-force current-base merge from
  `origin/migration/clean-runtime-baseline-reconstruct-v1` into this branch
  only if there are no conflicts and the final PR diff remains limited to
  `allowed_files`.

No labels, milestones, assignees, projects, PR branch deletion, remote branch
deletion, cleanup, or other GitHub changes are permitted.

## Hard Stops

- Do not touch product, runtime, data, extraction, parser, prompt, source-PDF,
  gold-label, DB, Qdrant, news, memory, service, model/GPU, or production-data
  files.
- Do not restore, clean, delete, stash, reset, rebase, cherry-pick, force-push,
  prune, branch-delete, or worktree-delete.
- Do not open or merge a PR for this closeout unless separately approved. The
  operator's 2026-06-26 `proceed` after the local closeout report commit is the
  separate approval for the bounded publish-and-merge-if-safe lane above.
- Do not modify the historical parity artifact at
  `reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/diff-check.json`.
- Do not run extraction work, broad validation, services, or production-data
  workflows.

## Close Gate

Issue #234 may be closed only if all of the following are true:

- Issue #234 is still open before the closeout action.
- PR #411 is merged into
  `migration/clean-runtime-baseline-reconstruct-v1`.
- PR #411 checks are green.
- Canonical head contains the preserved issue #234 report packet.
- The preserved classification is `SUPERSEDED_CURRENT_BASE_CLEAN`.
- Current canonical evidence shows the historical parity artifact is tracked
  clean and the stale dirty rewrite is absent.
- Remaining `DATA_MISSING` is limited to the historical 2026-06-02 writer and
  is non-blocking because the stale state no longer applies to canonical.
- The closeout diff is limited to this task card and report bundle.

## Required Reports

- `README.md`
- `status.json`
- `issue_closeout_matrix.md`
- `followup_issue_map.md`
- `data_missing.md`
- `github_closeout_comment.md`

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue234_closeout_v1_20260626.md`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/issue234_closeout_v1_20260626.md --repo-root . --no-write-report`
- `python3 -m json.tool reports/agent_jobs/issue234_closeout_v1_20260626/status.json`
- `git diff --check`
- Live `gh issue view 234 --repo 0rl4nd0l/tenn` verification after closeout.
