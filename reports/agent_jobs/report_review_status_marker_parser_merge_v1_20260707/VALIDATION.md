# Validation

## Commands Run Before Merge Evidence

### `pwd && git branch --show-current && git rev-parse HEAD && git remote -v && git rev-parse --abbrev-ref --symbolic-full-name @{u} && git status --short --untracked-files=all`

Result: pass.

- path: `/home/l4nd0/tenn-report-review-status-marker-parser-v1-20260707`
- branch: `control-plane/report-review-status-marker-parser-v1-20260707`
- HEAD: `91e1882dabea8c3354fda561294e9481c2af6c66`
- upstream: `origin/control-plane/report-review-status-marker-parser-v1-20260707`
- status: clean

### `python3 scripts/tenn_dev_status.py`

Result: pass.

- `GIT_STATUS: clean`
- `GUARD_RESULT: pass`
- `GUARD_PATH_CLASSIFICATION: VALID_TASK_WORKTREE`
- `GUARD_STOP_REIMPLEMENTATION: false`
- `GUARD_DUPLICATE_WORK: NO_MATCHING_ACTIVE_WORK_FOUND`
- `GUARD_REGISTRY: PASS`
- `GUARD_LEDGER: PASS`

### `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /home/l4nd0/tenn-report-review-status-marker-parser-v1-20260707 --topic "merge PR 485 report review status marker parser" --fallback-detail full --json`

Result: expected tooling-version failure.

The installed portable guard rejected `--fallback-detail full`:
`unrecognized arguments: --fallback-detail full`.

### `python3 .agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root . --topic "merge PR 485 report review status marker parser" --json`

Result: pass.

- `final_decision: pass`
- `path_ownership.classification: VALID_TASK_WORKTREE`
- `stop_reimplementation: false`
- `registry_status: PASS`
- `ledger_status: PASS`
- `duplicate_work_classification: NO_MATCHING_ACTIVE_WORK_FOUND`
- `canonical_head: 94dedc2913d4dbfc1913ca6fae897ca2ce4a0579`
- `head: 91e1882dabea8c3354fda561294e9481c2af6c66`

### `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`

Result: pass.

- `ok: true`
- `read_only: true`
- `active_jobs: []`

### `python3 scripts/agent_task_ledger.py validate`

Result: pass.

- `ok: true`
- `entry_count: 291`
- `issues: []`
- `data_missing: []`

### `gh pr view 485 --json number,title,state,isDraft,headRefName,baseRefName,url,mergeable,reviewDecision,statusCheckRollup,commits,changedFiles,updatedAt`

Result: pass.

- state: `OPEN`
- draft: `false`
- base: `migration/clean-runtime-baseline-reconstruct-v1`
- head: `control-plane/report-review-status-marker-parser-v1-20260707`
- mergeable: `MERGEABLE`
- changed files: `10`
- updatedAt: `2026-07-07T07:21:13Z`

### `gh pr checks 485`

Result: pass.

- `lint-and-test`: pass
- `scan`: pass

## Commands Run After Merge Evidence Creation

### `python3 scripts/agent_job_contract.py validate docs/agent_tasks/report_review_status_marker_parser_merge_v1_20260707.md`

Result: pass.

- `ok: true`
- `issues: []`
- `github_write_scope: push_merge_evidence_and_merge_pr_485_only`

### `python3 scripts/check_board_decision.py reports/agent_jobs/report_review_status_marker_parser_merge_v1_20260707/BOARD_DECISION.json`

Result: pass.

- `ok: true`
- `issues: []`

### `python3 -m unittest scripts.test_report_review_status`

Result: pass.

- `Ran 11 tests`
- `OK`

### `python3 scripts/report_review_status.py validate reports/agent_jobs/report_review_status_marker_parser_v1_20260707`

Result: pass.

- `ok: true`
- `review_status: DATA_MISSING`
- missing optional marker accepted as expected

### `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/report_review_status_marker_parser_merge_v1_20260707.md --no-write-report`

Result: pass.

- `ok: true`
- `disallowed_files: []`

### `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/report_review_status_marker_parser_merge_v1_20260707.md`

Result: pass.

- `ok: true`
- all five expected report files exist

### `git diff --check -- docs/agent_tasks/report_review_status_marker_parser_merge_v1_20260707.md reports/agent_jobs/report_review_status_marker_parser_merge_v1_20260707`

Result: pass.

## Commands Pending After This Commit

- staged allowlist check including force-added report artifacts
- commit and push merge evidence
- final PR check rerun after merge-evidence commit
- PR merge command and final PR state verification
