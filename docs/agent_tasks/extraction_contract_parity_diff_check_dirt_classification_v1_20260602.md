---
job_id: extraction_contract_parity_diff_check_dirt_classification_v1_20260602
owner: Codex
lane: Evaluation
supporting_lanes:
  - Repo Hygiene
status: approved
approval_required: false
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
output_dir: reports/agent_jobs/extraction_contract_parity_diff_check_dirt_classification_v1_20260602
allowed_files:
  - docs/agent_tasks/extraction_contract_parity_diff_check_dirt_classification_v1_20260602.md
  - reports/agent_jobs/extraction_contract_parity_diff_check_dirt_classification_v1_20260602/README.md
  - reports/agent_jobs/extraction_contract_parity_diff_check_dirt_classification_v1_20260602/ISSUE_REFRESH.md
  - reports/agent_jobs/extraction_contract_parity_diff_check_dirt_classification_v1_20260602/EVIDENCE.md
  - reports/agent_jobs/extraction_contract_parity_diff_check_dirt_classification_v1_20260602/CLASSIFICATION.md
  - reports/agent_jobs/extraction_contract_parity_diff_check_dirt_classification_v1_20260602/APPROVAL_PACKET.md
  - reports/agent_jobs/extraction_contract_parity_diff_check_dirt_classification_v1_20260602/DATA_MISSING.md
  - reports/agent_jobs/extraction_contract_parity_diff_check_dirt_classification_v1_20260602/VALIDATION.md
  - reports/agent_jobs/extraction_contract_parity_diff_check_dirt_classification_v1_20260602/PUBLISH_REFRESH.md
  - reports/agent_jobs/extraction_contract_parity_diff_check_dirt_classification_v1_20260602/CODE_REVIEW.json
timeout_seconds: 3600
---

# Extraction Contract Parity Diff-Check Dirt Classification

## Objective

Run the report-only issue #234 Phase 3 dry-run review under
`REPORT_AUTONOMY`. Classify the stale extraction contract parity
`diff-check.json` dirt described by issue #234 and produce an approval packet.

## Scope

This task may write only this task card and the report files listed in
`allowed_files`. It may read current Git state, the merged V2 auto-progress
bundle, issue #234, issue #98 metadata, registry read-only state, and existing
report/control evidence needed for classification.

## Hard Stops

- Do not touch the count-24 extraction approval packet.
- Do not mutate product, runtime, data, extraction, prompt, source-PDF,
  gold-label, DB, Qdrant, news, memory, service, model/GPU, or production-data
  files.
- Do not restore, clean, delete, stash, reset, rebase, cherry-pick, or
  force-push. Do not merge except one non-force merge of current
  `origin/migration/clean-runtime-baseline-reconstruct-v1` into PR #411's
  branch after explicit operator `proceed` approval, only to refresh the branch
  from base `b3b3a154590f36e61d297c1ac79fe623526f0b28` to current base
  `4f45aaa4a6de9d0ae151c27599a1e19621825382`.
- Do not mutate GitHub except opening the draft preservation PR, marking PR
  #411 ready, and merging PR #411 after explicit operator `proceed` approval,
  current-base refresh, clean task-card validation, clean code review, clean
  guard, and green GitHub checks.
- Do not close issue #234 in this publish or merge step.
- Do not start services.
- Do not run extraction work or broad validation.
- Do not modify the historical parity artifact at
  `reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/diff-check.json`.

## Preservation Refresh

On 2026-06-25, the operator approved proceeding from the repo/PR triage lane.
This permits replaying the already-committed report-only packet onto a fresh
current-base branch, committing the exact allowed files, pushing that branch,
and opening a draft PR. It does not permit issue closeout, branch deletion,
worktree deletion, cleanup, extraction work, broad validation, product/runtime/
data mutation, or changing the historical parity artifact.

On 2026-06-25 after PR #411 opened, CI passed and GitHub reported the PR
mergeable, but canonical advanced via PR #410. The operator then replied
`proceed` after being told the next safe lane was a current-base refresh plus
ready/merge authorization. This permits the PR #411 branch refresh, ready
transition, and merge only if the refreshed branch remains limited to this
task card and report bundle and all validation gates stay green. It does not
permit issue #234 closeout, cleanup, deletion, extraction work, or historical
parity artifact mutation.

## Required Report Files

- `README.md`
- `ISSUE_REFRESH.md`
- `EVIDENCE.md`
- `CLASSIFICATION.md`
- `APPROVAL_PACKET.md`
- `DATA_MISSING.md`
- `VALIDATION.md`

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_contract_parity_diff_check_dirt_classification_v1_20260602.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_contract_parity_diff_check_dirt_classification_v1_20260602.md --no-write-report`
- `git diff --check`
- Changed-path guard proving the diff is limited to this task card and report
  bundle.
- Code-reviewer JSON review of the exact diff.
- Green GitHub PR #411 checks after current-base refresh.
- Final merge verification that PR #411 merged into
  `migration/clean-runtime-baseline-reconstruct-v1`.
