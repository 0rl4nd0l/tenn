---
job_id: report_review_status_marker_parser_merge_v1_20260707
lane: Reporting
supporting_lanes:
  - Evaluation
owner: Codex
approval_required: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/report_review_status_marker_parser_merge_v1_20260707
mutation_mode: safe_extension
production_data_access: false
task_scope: merge_pr_485_only
github_write_scope: push_merge_evidence_and_merge_pr_485_only
target_pr: 485
target_branch: control-plane/report-review-status-marker-parser-v1-20260707
target_commit_before_merge_evidence: 91e1882dabea8c3354fda561294e9481c2af6c66
pr_base: origin/migration/clean-runtime-baseline-reconstruct-v1
allowed_files:
  - docs/agent_tasks/report_review_status_marker_parser_merge_v1_20260707.md
  - reports/agent_jobs/report_review_status_marker_parser_merge_v1_20260707/README.md
  - reports/agent_jobs/report_review_status_marker_parser_merge_v1_20260707/VALIDATION.md
  - reports/agent_jobs/report_review_status_marker_parser_merge_v1_20260707/BOARD.md
  - reports/agent_jobs/report_review_status_marker_parser_merge_v1_20260707/BOARD_DECISION.json
  - reports/agent_jobs/report_review_status_marker_parser_merge_v1_20260707/NEXT_GOAL.md
---

# Report Review Status Marker Parser Merge V1

## Approval

USER_APPROVED: Orlando said `proceed` after PR #485 was marked ready for
review, mergeable, and green on GitHub checks.

## Objective

Merge PR #485, `[codex] Add report review status marker parser`, only if final
guard, task-card, board, and GitHub checks remain clean.

## Scope

- Verify the PR #485 branch worktree and GitHub state.
- Record merge-readiness evidence and review-board decision.
- Push only this merge evidence commit to the PR branch.
- Wait for the resulting PR checks.
- Merge PR #485 into `migration/clean-runtime-baseline-reconstruct-v1` only if
  it remains open, non-draft, mergeable, and green.
- Verify final PR state after merge.

## Out Of Scope

- No parser/helper code changes.
- No automation runner behavior changes.
- No runtime, data, extraction, parser-output, source-PDF, gold-label, DB,
  Qdrant, Redis, news-store, memory-store, timer, systemd, Docker, service,
  model/GPU, or secret mutation.
- No issue create, close, label, reopen, or comment.
- No live registry or live task-ledger mutation.
- No branch deletion, worktree deletion, cleanup, rebase, reset, stash,
  cherry-pick, force-push, or parking action.

## Validation Plan

- `python3 scripts/tenn_dev_status.py`
- `python3 .agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "merge PR 485 report review status marker parser" --json`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_task_ledger.py validate`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/report_review_status_marker_parser_merge_v1_20260707.md`
- `python3 scripts/check_board_decision.py reports/agent_jobs/report_review_status_marker_parser_merge_v1_20260707/BOARD_DECISION.json`
- `python3 -m unittest scripts.test_report_review_status`
- `python3 scripts/report_review_status.py validate reports/agent_jobs/report_review_status_marker_parser_v1_20260707`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/report_review_status_marker_parser_merge_v1_20260707.md --no-write-report`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/report_review_status_marker_parser_merge_v1_20260707.md`
- `git diff --check`
- `gh pr view 485 --json number,title,state,isDraft,headRefName,baseRefName,url,mergeable,reviewDecision,statusCheckRollup,commits,changedFiles,updatedAt`
- `gh pr checks 485`
- final `gh pr merge 485 --merge` only if all gates pass
