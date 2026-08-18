---
job_id: report_review_status_marker_parser_v1_20260707
lane: Reporting
supporting_lanes:
  - Evaluation
owner: Codex
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/report_review_status_marker_parser_v1_20260707
mutation_mode: safe_extension
production_data_access: false
task_scope: control_plane_only
allowed_files:
  - docs/agent_tasks/report_review_status_marker_parser_v1_20260707.md
  - scripts/report_review_status.py
  - scripts/test_report_review_status.py
  - reports/agent_jobs/report_review_status_marker_parser_v1_20260707/README.md
  - reports/agent_jobs/report_review_status_marker_parser_v1_20260707/STATE.md
  - reports/agent_jobs/report_review_status_marker_parser_v1_20260707/VALIDATION.md
  - reports/agent_jobs/report_review_status_marker_parser_v1_20260707/DECISIONS.md
---

# Report Review Status Marker Parser V1

## Approval

USER_APPROVED: Orlando said `proceed` after the report-review marker audit
recommended this parser/helper as the next narrow implementation slice.

## Objective

Implement a small control-plane helper for parsing and validating optional
`REPORT_REVIEW_STATUS.json` files under `reports/agent_jobs/<job_id>/`.

## Scope

- Add a helper module with importable parsing/validation functions.
- Add focused tests for missing marker semantics, valid marker parsing, invalid
  status rejection, job-id mismatch rejection, and runtime-proof guard behavior.
- Keep missing marker semantics as `DATA_MISSING`, not failure.
- Keep the helper advisory only; it must not imply runtime functionality,
  GitHub state, PR readiness, financial-truth approval, or issue-closeout
  permission.

## Out Of Scope

- No historical report backfill.
- No automation runner prompt or behavior edits.
- No runtime, data, extraction, parser-output, source-PDF, gold-label, DB,
  Qdrant, Redis, news-store, memory-store, timer, systemd, Docker, service,
  model/GPU, or secret mutation.
- No GitHub writes.
- No live registry or live task-ledger mutation.
- No preserved task-card branch/worktree adoption, parking, deletion, merge, or
  cleanup.

## Validation Plan

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/report_review_status_marker_parser_v1_20260707.md`
- `python3 -m unittest scripts.test_report_review_status`
- `python3 scripts/report_review_status.py --help`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/report_review_status_marker_parser_v1_20260707.md --no-write-report`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/report_review_status_marker_parser_v1_20260707.md`
- `python3 scripts/agent_job_contract.py check-closeout docs/agent_tasks/report_review_status_marker_parser_v1_20260707.md`
- `git diff --check`
- `git status --short --untracked-files=all`
