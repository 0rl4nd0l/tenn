# Automation Small Model Routing V1 State

Status: DONE_WITH_RISK

## Current Evidence

- Task worktree:
  `/home/l4nd0/tenn-automation-small-model-routing-v1-20260710`
- Branch: `control-plane/automation-small-model-routing-v1-20260710`
- Base HEAD: `ed481f4a333d3d62e944ccd48a6fcdccbfb67068`
- Draft PR: `#499`, open against
  `migration/clean-runtime-baseline-reconstruct-v1` under later explicit owner
  approval.
- Tenn guard: pass before task-card creation.
- Tenn guard before review fixes: pass; duplicate work
  `NO_MATCHING_ACTIVE_WORK_FOUND`; registry `PASS`; ledger `PASS`.
- Focused unit tests before review fixes: 13 tests passed.
- Review-fix RED proof: 16 tests ran with one expected failure because invalid
  reasoning effort `medum` did not yet raise.
- Dry-run proof:
  - `repo-hygiene` command includes `--model gpt-5.4-mini` and
    `model_reasoning_effort="medium"`.
  - `extraction-regression` command has no explicit model override and keeps
    the configured Codex default.

## Boundaries

- Repo-side runner, tests, docs, and report artifacts only.
- No live timer/service/runtime/data mutation.
- GitHub mutation is limited to the approved branch push and draft PR #499.
- No PR review comment, ready-for-review transition, merge, or live
  execution-surface mutation.

## Task Ledger And Routing

- Task Ledger: `PASS`; no live ledger mutation was needed for this continuation
  of the existing PR lane.
- Duplicate work: `NO_MATCHING_ACTIVE_WORK_FOUND`.
- `task_tier`: `medium`
- `recommended_model`: standard coding model
- `actual_model`: current Codex session model; exact deployment
  `DATA_MISSING`
- `why_this_model`: bounded multi-file control-plane review fix with command
  construction and validation behavior
- `worker_model_allowed`: false
- `worker_decision_limit`: no workers used
- `escalation_needed`: false

## Docs Impact Check

- `docs_impact`: `DOCS_UPDATED`
- `docs_checked`: `docs/dev/automation_index.md`, task card, state, validation
- `docs_changed`: override precedence, supported reasoning values, and later
  PR approval/current state
- `docs_followup`: none
- `reason`: operator-visible environment behavior and durable approval state
  changed

## Runtime / Rollout Caveat

This change is proven in the task worktree by command-construction tests and
dry-run output. It does not mutate the installed user timers or the automation
execution worktree. Live scheduled automations will use the new routing only
after this branch is merged and the execution surface is updated to that
content.

## Runtime Functionality Proof

| Field | Required evidence |
| --- | --- |
| intended output | A scheduled low-risk automation invokes `gpt-5.4-mini` and produces its expected report. |
| live output location | `/home/l4nd0/.codex/automations/tenn/reports/` and `/home/l4nd0/.codex/automations/tenn/logs/`. |
| pre-run max timestamp or count | DATA_MISSING; no live run was authorized. |
| post-run max timestamp or count | DATA_MISSING; no live run was authorized. |
| rows/files inserted or updated after run start | Zero live automation outputs attributable to this control-plane task. |
| readiness/gate status | Repo command-construction gate only; merge and execution-surface rollout remain pending. |
| exact command/query used | DATA_MISSING; live automation command was not run. |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | DATA_MISSING |
| remaining blocker | Merge, separately approved execution-surface rollout, and fresh scheduled-job output proof. |

## Next Step

Push the review-fix commit to draft PR #499 and await fresh CI. Merge and any
automation execution-surface update remain separate explicit approvals.
