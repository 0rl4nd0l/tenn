# State

State: PR_READY

Current Focus: Repair a current-canonical closeout self-check gap caused by a
historical control-plane task card that predates the explicit exemption
metadata.

## Evidence

- Current canonical branch: `origin/migration/clean-runtime-baseline-reconstruct-v1`
  at `f195e90d464f49916f6626242ca26d74580dc0a1`.
- PR #385 and PR #386 are already merged.
- `check-closeout` on the PR #385 task card failed because the card has
  runtime-like words but did not explicitly declare a control-plane-only
  closeout scope.

## Scope

- Add explicit `closeout_scope: control_plane_only` to the PR #385 task card.
- Preserve the existing validator behavior and tests unchanged.
- Do not touch greyhound runtime, Tenn product/runtime/data/extraction/count-24,
  or host-global files.

## Docs Impact

- docs_impact: DOCS_NOT_REQUIRED
- docs_checked: AGENTS.md, CODEX_OPERATOR_GUIDE.md, CONTROL_PLANE_OPEN_WORK.md,
  CONTROL_PLANE_STATUS.md
- docs_changed: none
- docs_followup: none
- reason: Existing docs already describe explicit closeout-scope metadata; this
  repair applies that metadata to one historical task card.

## Model And Worker Routing

- task_tier: small
- recommended_model: standard coding model
- actual_model: GPT-5 Codex
- why_this_model: narrow task-card/report consistency repair with focused
  validation
- worker_model_allowed: false
- worker_decision_limit: none
- escalation_needed: false

## Runtime Functionality Proof

- Required: no
- Reason: control-plane metadata/report repair only; no runtime functionality is
  being claimed.

## Task Ledger

- live ledger: DATA_MISSING
- committed ledger: present
- duplicate-work classification: no self-consistency lane found; PR #385/#386
  merged the underlying gate and exemption logic
- ledger update result: report-local only

## Validation

- The formerly failing PR #385 `check-closeout` and `check-report-artifacts`
  commands now pass.
- Focused contract/hook tests pass: 58 tests.
- Visible repo-backed skill count stayed at 10.
