# State

status: done_control_plane_only

## Summary

Implemented the second control-plane hardening slice: `check-closeout` now
validates listed `BOARD_DECISION.json` report artifacts through the existing
board-decision validator.

## Current Git State

- Worktree: `/home/l4nd0/tenn`
- Branch: `local/tenn-entrypoint-current-baseline-v1-20260623`
- Base refresh: approved option A; merged
  `origin/migration/clean-runtime-baseline-reconstruct-v1` into this branch.
- Draft PR: #400, already open for this branch.

## Implemented

- Added board-decision artifact detection in `scripts/agent_job_contract.py`.
- Kept validator import lazy so hook smoke repos without
  `scripts/check_board_decision.py` continue to work unless a board decision is
  actually present.
- Extended `check-report-artifacts` and runtime closeout to validate listed
  board decisions when full report artifacts are checked.
- Extended non-runtime `check-closeout` to validate listed
  `BOARD_DECISION.json` without forcing all report artifacts to exist.
- Added red/green tests for invalid and valid non-runtime board closeout.
- Updated operator/status docs to describe automatic closeout validation.

## Boundaries Preserved

- No runtime, product, extraction, source PDF, gold-label, prompt, DB, Qdrant,
  Redis, news, memory, model/GPU, service, or production-data mutation.
- No GitHub issue mutation, merge, rebase, branch deletion, or force-push.
- No host/global Codex skill sync and no `.codex` surface mutation.

## Task Ledger And Duplicate Work

- Task Ledger validate: PASS, 17 entries, no data-missing sources.
- Registry read-only check: PASS, zero active jobs.
- Tenn git guard duplicate-work classification:
  `NO_MATCHING_ACTIVE_WORK_FOUND`.
- Live ledger mutation was not required; this report records the implementation
  state.

## Docs Impact

- docs_impact: DOCS_UPDATED
- docs_checked:
  - `docs/dev_flow/CODEX_OPERATOR_GUIDE.md`
  - `docs/dev_flow/CONTROL_PLANE_STATUS.md`
- docs_changed:
  - `docs/dev_flow/CODEX_OPERATOR_GUIDE.md`
  - `docs/dev_flow/CONTROL_PLANE_STATUS.md`
- docs_followup: none
- reason: closeout behavior changed and operator-facing docs needed to state
  that listed `BOARD_DECISION.json` artifacts are now validated by
  `check-closeout`.

## Model And Worker Routing

- task_tier: medium
- recommended_model: standard coding model
- actual_model: GPT-5 Codex
- why_this_model: shared control-plane closeout tooling needed a focused
  implementation and regression tests.
- worker_model_allowed: no
- worker_decision_limit: none
- escalation_needed: none after owner approved branch-refresh option A.

## Runtime Functionality Proof

Not applicable. This was control-plane closeout tooling and documentation work,
not daemon, runtime, ingestion, extraction, automation, collector, scheduler,
service, or pipeline work.
