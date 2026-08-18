---
job_id: report_review_status_marker_parser_publish_v1_20260707
lane: Reporting
supporting_lanes:
  - Evaluation
owner: Codex
approval_required: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/report_review_status_marker_parser_publish_v1_20260707
mutation_mode: safe_extension
production_data_access: false
task_scope: publish_only
github_write_scope: push_branch_and_open_draft_pr_only
target_branch: control-plane/report-review-status-marker-parser-v1-20260707
target_commit: d77ba8d8738d77dc7ddc67e0d3b7841d50d39de6
pr_base: origin/migration/clean-runtime-baseline-reconstruct-v1
allowed_files:
  - docs/agent_tasks/report_review_status_marker_parser_publish_v1_20260707.md
  - reports/agent_jobs/report_review_status_marker_parser_publish_v1_20260707/README.md
  - reports/agent_jobs/report_review_status_marker_parser_publish_v1_20260707/VALIDATION.md
---

# Report Review Status Marker Parser Publish V1

## Approval

USER_APPROVED: Orlando said `proceed` after the recommended next step was to
publish `report_review_status_marker_parser_v1_20260707`.

## Objective

Publish the existing local parser/helper commit as a draft PR.

## Scope

- Verify the clean task worktree and local commit.
- Rerun focused validation.
- Push branch `control-plane/report-review-status-marker-parser-v1-20260707` to
  origin.
- Open a draft PR against `migration/clean-runtime-baseline-reconstruct-v1`.
- Record PR state in the report bundle.

## Out Of Scope

- No parser/helper code changes.
- No automation runner behavior changes.
- No historical report backfill.
- No runtime, data, extraction, parser-output, source-PDF, gold-label, DB,
  Qdrant, Redis, news-store, memory-store, timer, systemd, Docker, service,
  model/GPU, or secret mutation.
- No ready-for-review transition.
- No issue close, label, comment, or merge action.
- No live registry or live task-ledger mutation.
- No branch cleanup, rebase, reset, stash, force-push, or deletion.

## Validation Plan

- `python3 scripts/tenn_dev_status.py`
- `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /home/l4nd0/tenn-report-review-status-marker-parser-v1-20260707 --topic "publish report_review_status_marker_parser_v1_20260707 draft PR" --json`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/report_review_status_marker_parser_publish_v1_20260707.md`
- `python3 -m unittest scripts.test_report_review_status`
- `python3 scripts/report_review_status.py validate reports/agent_jobs/report_review_status_marker_parser_v1_20260707`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/report_review_status_marker_parser_publish_v1_20260707.md --no-write-report`
- `git diff --check`
- `gh pr list --state all --head control-plane/report-review-status-marker-parser-v1-20260707 --json number,title,state,headRefName,baseRefName,url,updatedAt`
- post-PR `gh pr view`
