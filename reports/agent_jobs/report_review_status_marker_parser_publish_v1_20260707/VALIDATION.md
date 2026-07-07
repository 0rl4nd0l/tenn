# Validation

## Preflight

- target worktree:
  `/home/l4nd0/tenn-report-review-status-marker-parser-v1-20260707`
- branch:
  `control-plane/report-review-status-marker-parser-v1-20260707`
- starting HEAD:
  `d77ba8d8738d77dc7ddc67e0d3b7841d50d39de6`
- upstream:
  `origin/migration/clean-runtime-baseline-reconstruct-v1`
- starting status:
  clean
- `python3 scripts/tenn_dev_status.py`:
  exit 0; clean, `VALID_TASK_WORKTREE`, duplicate work
  `NO_MATCHING_ACTIVE_WORK_FOUND`, registry pass, ledger pass.
- portable guard:
  exit 0; `final_decision=pass`,
  `path_ownership=VALID_TASK_WORKTREE`, `registry_status=PASS`,
  `ledger_status=PASS`, `duplicate_work_classification=NO_MATCHING_ACTIVE_WORK_FOUND`.
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`:
  exit 0; `active_jobs=[]`.
- `python3 scripts/agent_task_ledger.py validate`:
  exit 0; `ok=true`, `entry_count=291`.
- `gh --version`:
  exit 0; `gh version 2.4.0+dfsg1`.
- `gh auth status`:
  exit 0; logged in as `0rl4nd0l`.
- existing PR checks:
  - `gh pr list --state all --head control-plane/report-review-status-marker-parser-v1-20260707 ...`:
    exit 0; `[]`.
  - `gh pr list --state all --search "report_review_status_marker_parser_v1_20260707" ...`:
    exit 0; `[]`.

## Focused Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/report_review_status_marker_parser_publish_v1_20260707.md`:
  exit 0; `ok=true`.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/report_review_status_marker_parser_publish_v1_20260707.md --no-write-report`:
  exit 0; `ok=true`, `disallowed_files=[]`.
- `python3 -m unittest scripts.test_report_review_status`:
  exit 0; eleven tests passed.
- `python3 scripts/report_review_status.py validate reports/agent_jobs/report_review_status_marker_parser_v1_20260707`:
  exit 0; missing marker returns `review_status=DATA_MISSING`, `ok=true`.
- `python3 -m py_compile scripts/report_review_status.py scripts/test_report_review_status.py`:
  exit 0.
- `git diff --check`:
  exit 0.
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/report_review_status_marker_parser_publish_v1_20260707.md`:
  exit 0; `ok=true`, report artifacts present and non-empty.

## Publish Actions

- `git commit -m "Add parser publish task card"`:
  exit 0; committed publish task card and report artifacts as
  `3cf7097b`.
- `git push -u origin control-plane/report-review-status-marker-parser-v1-20260707`:
  exit 1; blocked by pre-push hook.

```text
[pre-push] missing required hook tool(s): ruff at /home/l4nd0/tenn-report-review-status-marker-parser-v1-20260707/financial-engine_v2/.venv/bin/ruff pytest at /home/l4nd0/tenn-report-review-status-marker-parser-v1-20260707/financial-engine_v2/.venv/bin/pytest
[pre-push] set TENN_ALLOW_MISSING_HOOK_TOOLS=1 to bypass local tool checks intentionally
error: failed to push some refs to 'https://github.com/0rl4nd0l/tenn.git'
```

## Final State

WAITING_ON_USER.

Needed: owner approval either to intentionally set
`TENN_ALLOW_MISSING_HOOK_TOOLS=1` for this push, or to repair/install the
missing hook tools in `financial-engine_v2/.venv`.
