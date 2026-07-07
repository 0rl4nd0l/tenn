# Report Review Status Marker Parser Publish V1

## Objective

Publish local commit `d77ba8d8738d77dc7ddc67e0d3b7841d50d39de6` from branch
`control-plane/report-review-status-marker-parser-v1-20260707` as a draft PR
against `migration/clean-runtime-baseline-reconstruct-v1`.

## Current State

RUNNING

## Scope

- Push branch to origin.
- Open draft PR only.
- Record PR state.

## Files Touched

- `docs/agent_tasks/report_review_status_marker_parser_publish_v1_20260707.md`
- `reports/agent_jobs/report_review_status_marker_parser_publish_v1_20260707/README.md`
- `reports/agent_jobs/report_review_status_marker_parser_publish_v1_20260707/VALIDATION.md`

## Files Intentionally Not Touched

- parser/helper code
- parser/helper tests
- automation runner behavior
- historical report bundles
- runtime/data/extraction/parser-output/source-PDF/gold-label/prompt surfaces
- DB, Qdrant, Redis, news stores, memory stores, production data
- timers, systemd, Docker volumes, model/GPU config, services
- ready-for-review state, issue close/comment/label, merge, rebase, reset,
  stash, force-push, branch deletion, worktree deletion
- live registry and live task ledger

## Validation Status

See `VALIDATION.md`.

## PR State

Pending. User approved the explicit local pre-push hook-tool bypass after the
first push attempt was blocked by missing local Ruff/pytest binaries.

## Bypass Approval

USER_APPROVED: Orlando selected option A, approving:

```bash
TENN_ALLOW_MISSING_HOOK_TOOLS=1 git push -u origin control-plane/report-review-status-marker-parser-v1-20260707
```

Scope remains limited to pushing this already-validated branch and opening a
draft PR. No runtime/data/extraction/automation behavior changes are allowed.

## Prior WAITING_ON_USER

Needed: choose one publish path.

Why: `git push` failed because the pre-push hook requires Ruff and pytest in
`financial-engine_v2/.venv`, and that local venv does not currently provide
them.

Current safe state:

- publish evidence is committed locally
- branch is clean except ignored `scripts/__pycache__/`
- branch is ahead of the base by local commits
- no GitHub PR was opened
- no runtime/data/extraction surfaces were touched

Options:

- A: approve intentional hook-tool bypass for this already-validated branch:
  `TENN_ALLOW_MISSING_HOOK_TOOLS=1 git push -u origin control-plane/report-review-status-marker-parser-v1-20260707`
- B: approve installing/repairing `ruff` and `pytest` in
  `financial-engine_v2/.venv`, then rerun push without bypass
- C: stop here and leave the branch local

Recommended: A, because focused validation already passed and repairing the
repo venv is broader than this publish-only lane.

## Runtime Functionality Proof

- Required: no.
- intended output: GitHub draft PR for existing control-plane helper commit.
- live output location: GitHub pull request.
- pre-run max timestamp or count: no existing PR for this branch.
- post-run max timestamp or count: zero PRs created.
- rows/files inserted or updated after run start: none; GitHub PR only.
- readiness/gate status: owner approved bypass; push/PR pending.
- exact command/query used: see `VALIDATION.md`.
- result: DATA_MISSING until PR is created and verified.
- remaining blocker: push/PR pending.
