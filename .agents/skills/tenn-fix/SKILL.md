---
name: tenn-fix
description: Tenn bounded implementation orchestrator. Reads issue or board artifacts, runs Git guard, validates task-card scope, deploys workers only when useful, integrates one coherent change, validates, reviews, and prepares PRs only when allowed.
---

# Tenn Fix

Use `tenn-fix` when Orlando asks for implementation after an issue packet,
board decision, task card, handoff, or explicit fix request.

`tenn-fix` is an orchestrator. It owns scope, validation, review, and closeout.

## Workflow

1. Read `ISSUE.md`, `BOARD_DECISION.json`, task card, or the current user fix
   request.
2. Run `tenn-git-guard` preflight and inspect `path_ownership`,
   `canonical_head`, `duplicate_work_status`, and `stop_reimplementation`.
3. Stop when the guard returns `OPEN_PR_WAIT` or `MERGED_USE_CANONICAL` unless
   Orlando explicitly overrides with continue, adopt, or supersede instructions.
   Stop on `OWNER_BOUNDARY` or `UNKNOWN_ASK` when the next meaningful step needs
   an owner decision.
   When `path_ownership.classification` is `STALE_PATH`, the checkout is clean,
   and registry, ledger, and duplicate-work evidence show no conflict, create a
   fresh sibling task worktree from canonical and rerun preflight there.
   Otherwise stop when `path_ownership.classification` is not a valid clean
   canonical/task worktree. Ask Orlando only for dirty state, branch/path
   collision, destructive cleanup, duplicate active work, unclear task scope,
   runtime/data mutation, GitHub mutation, or reset/rebase/stash/clean/delete
   decisions.
4. Create or validate a task card before any mutation.
5. Confirm every intended path is inside the task-card `allowed_files`.
6. Write or update Task Ledger state when the workflow is implementation-capable:
   `claimed` at task acceptance, `implementation_started` before edits,
   `blocked` or `waiting_on_user` before stopping, `pr_opened` after PR
   creation, and `done`, `merged`, `parked`, or `superseded` at closeout as
   applicable. Use `waiting_on_timer` for timer waits and `owner_boundary` when
   ownership or approval blocks progress. Prefer
   `python3 scripts/agent_task_ledger.py append` only when live ledger mutation
   is allowed by the task card or owner approval. Otherwise write the intended
   entry under the report bundle and record why live append was skipped. If the
   ledger file is unavailable, record `DATA_MISSING` in the report and continue
   only after the guard's bounded fallback search is clean.
7. Do not implement from a headline metric, score, count, pass rate, daemon
   status, or evaluation result until denominator, filters, exclusions,
   freshness, and pipeline stage are understood. Use counter-lineage evidence
   when the number is surprising or challenged.
   If the user says or implies "we fixed this already", "broken again",
   "regressed", "same bug", "why is this still broken", or equivalent, run the
   Regression Adjudication workflow in
   `docs/dev_flow/REGRESSION_ADJUDICATION.md` before coding. Classify the case
   as `STALE_BRANCH`, `FIX_NOT_IN_CANONICAL`, `NARROW_FIX_ONLY`,
   `RUNTIME_NOT_PROVEN`, `TEST_GAP`, `NEW_FAILURE_CLASS`, `TRUE_REGRESSION`, or
   `DATA_MISSING`, then choose the matching next action. Do not patch from the
   headline symptom until target identity, old-fix lineage, current repro,
   permanent gate, and runtime proof status are explicit.
8. Before closeout on daemon, runtime, ingestion, extraction, automation,
   collector, scheduler, service, or pipeline work, complete the
   `Runtime Functionality Proof` table from `AGENTS.md`. If intended live output
   is stale, zero, missing, or unverified, close as `PARTIAL`, `BROKEN`, or
   `DATA_MISSING`; if only tests, reports, artifacts, logs, timers, services, or
   PR state changed, use `DONE_WITH_RISK` or `PARTIAL`, not `DONE`.
9. Default to the smallest safe diff first. If one readable line solves the
   task, change one line; remove unnecessary related lines only when safely in
   scope.
10. Use RED/GREEN validation where practical: capture a failing regression test
   or focused check before the fix, then rerun after the change.
11. Execute one bounded milestone per run.
12. Classify task difficulty and record model/worker routing before delegating
   or making high-risk decisions.
13. Delegate bounded workers only when they reduce risk or context load. Use
   `docs/dev_flow/templates/WORKER_TASK.md` and `WORKER_RESULT.md`; each worker
   gets one lane, one worktree, one brief, one result file, and no shared
   mutation surface.
14. Integrate one coherent change at a time.
15. Run focused validation proportional to blast radius.
16. Perform a Docs Impact Check before code review and closeout.
17. Run the final PR/diff review gate before PR preparation. Use
   `docs/dev_flow/templates/PR_REVIEW.md` and the host code-reviewer stance
   only inside Tenn task-card, registry, validation, and forbidden-path gates.
18. Prepare, push, or open a PR only when the task and owner approval permit it.
19. When stopping before completion, run or follow `tenn-handoff` so the next
    session has git state, ledger state, validation, and a short next `/goal`.

## Action-First Small Fix Mode

Use this mode for `FAST_PROGRESS`: small docs/control-plane fixes or narrow
code fixes with exact files, a valid clean worktree, no stale/dirty/duplicate
blocker, no runtime/data/extraction/GitHub/destructive boundary, and no
owner-boundary decision.

In this mode:

1. Run the default summarized `tenn-git-guard` preflight and inspect
   `path_ownership`, `duplicate_work_status`, and `stop_reimplementation`.
2. Create or validate the smallest exact task card needed for edits.
3. Patch only the allowed files.
4. Run the cheapest focused validation that exercises the change.
5. Close out with files touched, validation command/result, unsafe actions
   avoided, and exact next action.

Do not run a review board, handoff, worker delegation, broad report packet, or
full fallback branch/worktree scan in `FAST_PROGRESS` unless the guard,
validation, or user request creates a real blocker. Escalate to `FULL_GUARD`
when eligibility is uncertain.

## Regression Adjudication Mode

Use this mode before implementation when a failure appears to resurface after a
prior claimed fix.

1. Read `docs/dev_flow/REGRESSION_ADJUDICATION.md`.
2. Freeze target identity with the normal guard preflight.
3. Find the alleged old fix by commit, PR, branch, report, task card, issue, or
   handoff.
4. Prove whether that fix is in the selected canonical path or active runtime
   surface.
5. Reproduce the current failure with the smallest exact command, query, input,
   or artifact check.
6. Classify the failure using the workflow's exact classification set.
7. Add or name the permanent regression gate before claiming the fix.
8. For runtime-like work, run the Runtime Functionality Proof table before
   saying working, fixed, complete, or `DONE`.

Classification controls action:

- `STALE_BRANCH`: retarget to canonical or active runtime surface.
- `FIX_NOT_IN_CANONICAL`: adopt, review, merge, park, or supersede existing
  work instead of reimplementing.
- `NARROW_FIX_ONLY`: turn the work into a failure-class task with a class-level
  gate.
- `RUNTIME_NOT_PROVEN`: prove the intended live output before fixing again.
- `TEST_GAP`: add the missing gate first or with the fix.
- `NEW_FAILURE_CLASS`: scope a new narrow fix and avoid claiming the old fix
  failed unless equivalence is proven.
- `TRUE_REGRESSION`: use red/green repair and preserve the failing command.
- `DATA_MISSING`: stop or continue only with labeled read-only evidence
  gathering.

## Fresh-Session Orchestrator Mode

Use this mode when a fresh Codex session is asked to continue from a
`HANDOFF.md`, problem statement, long repair, review-board decision, or worker
batch.

1. Read the handoff/problem statement first. Do not rely on chat memory when a
   report-local artifact exists.
2. Run `tenn-git-guard`, task-card validation, ledger validation, active
   registry read-only check, and duplicate-work search before editing.
3. Reconstruct the real objective, hard boundaries, relevant artifacts, failed
   attempts, known risks, and owner decisions from the handoff.
4. Break the work into independent lanes. Keep coupled work in the main
   orchestrator lane instead of delegating it.
5. Delegate only when lanes are independent and the task card can give each
   worker exact allowed files, decision limit, result path, and stop condition.
6. Each worker brief must name lane, worktree, branch, task card, allowed
   files, validation expected, result path, decision limit, and stop condition.
7. Workers may gather evidence, recommend, bid strategy, or perform bounded
   implementation only inside their explicit lane. Small/cheap workers must not
   make final high-risk, owner-boundary, financial-truth, merge, cleanup, or
   destructive decisions.
8. Review every worker output before integration. Record accepted, revised,
   parked, discarded, or owner-decision-needed status.
9. Integrate one coherent change at a time. Re-run the focused validation for
   the integrated change before moving to the next lane.
10. Stop and write `tenn-handoff` when the next meaningful step needs owner
    approval, unsafe path expansion, GitHub mutation not covered by the task
    card, product/runtime/data/extraction access, or unresolved `DATA_MISSING`.

## Docs Impact Check

Every implementation-capable run must perform a Docs Impact Check before
closeout. This is Codex development-tooling discipline, not Tenn runtime code.

If behavior, schema, command usage, workflow, validation, operator steps,
artifact shape, API, data model, skill trigger, or safety boundary changed,
update affected docs/templates/skills in the same task or create a
`DOCS_FOLLOWUP`.

If no docs update is required, record `DOCS_NOT_REQUIRED` with a reason. Do not
close out a PR with undocumented behavior changes.

Closeout must record:

- `docs_impact`: `DOCS_NOT_REQUIRED | DOCS_UPDATED | DOCS_FOLLOWUP | DATA_MISSING`
- `docs_checked`
- `docs_changed`
- `docs_followup`
- `reason`

For durable docs, templates, and skills, prefer freshness metadata when useful:
`last_verified_commit`, `last_verified_pr`, `source_of_truth_files`,
`stale_if_files`, `owner`, and `evidence_grade`.

## Model And Worker Routing

Classify the task before choosing workers or final decision authority:

- `small`: grep/search, JSON parse, file listing, report summarization, simple
  docs update, focused test run. Recommended model: mini/low-cost.
- `medium`: small bug fix, one/two-file code change, targeted regression, PR
  comment fix. Recommended model: standard coding model.
- `large`: multi-file correctness, schema/persistence, architecture change, or
  tricky debugging. Recommended model: high reasoning.
- `critical`: DB/runtime mutation, destructive Git, financial truth, merge
  conflict, high-risk cleanup, or owner-boundary decision. Recommended model:
  high reasoning plus `tenn-review-board`.

Record:

- `task_tier`
- `recommended_model`
- `actual_model`
- `why_this_model`
- `worker_model_allowed`
- `worker_decision_limit`
- `escalation_needed`

Use smaller/cheaper workers for bounded evidence gathering. Use high reasoning
models for architecture, schema, financial truth, merge readiness, destructive
operations, and owner-boundary decisions. Do not let a small model make final
decisions on high-risk work.

For hard tasks, optionally use a short strategy-bid stage: multiple read-only
workers propose compact plans, then the orchestrator selects one based on
testability, blast radius, value, and cost. Delegate subagents only when lanes
are independent and can be isolated by worktree, branch, result file, and
task-card allowlist.

The orchestrator, not the worker, owns final scope, integration, validation,
PR readiness, owner-boundary escalation, and closeout.

## Validation Environment Autonomy

If a requested validation command fails because a standard validation tool is
missing, try safe existing or ephemeral validation environments before blocking.

Resolution order:

1. existing repo venv
2. documented repo test command
3. available dependency runner such as `uv`
4. ephemeral venv under `/tmp` or another throwaway path
5. `unittest` or stdlib fallback when equivalent
6. `WAITING_ON_USER` only after safe paths fail

Agents may install standard validation-only dependencies such as `pytest` into
an ephemeral environment when:

- no repo dependency files or lockfiles are changed
- no production/runtime venv is modified
- the dependency is only used for validation
- the command and result are recorded

Do not mutate project dependencies, CI config, system packages, runtime
services, or host-global config without explicit approval.

## Task-Card And Registry Safety

The old `tenn-task-card-registry-safety` skill is merged into `/fix` and
`tenn-git-guard`. Before editing, validate the task card, compare every
intended path to `allowed_files`, inspect registry state through
`list-active --read-only`, and stop instead of widening scope when dirty state
or ownership is unclear.

## Outputs

Produce or update:

- `STATE.md`
- `DECISIONS.md`
- validation notes
- `NEXT_GOAL.md`

`STATE.md` or `DECISIONS.md` must record Task Ledger availability, current
ledger status, duplicate-work classification, ledger update result, and any
`DATA_MISSING` fallback searches.

`STATE.md`, `DECISIONS.md`, or the report bundle must also record Docs Impact
Check fields and Model/Worker Routing fields for the run.

For daemon, runtime, extraction, ingestion, automation, collector, scheduler,
service, or pipeline closeout, `STATE.md`, `DECISIONS.md`, or the report bundle
must also record the `Runtime Functionality Proof` result from `AGENTS.md`.

Closeout must be one of: PR opened, local commit, failing regression test,
issue closed, owner decision, or blocked with exact reason. Do not complete with
a report-only artifact unless it directly unlocks one of those outcomes.

For long or risky runs, fold Frame Design into `STATE.md` and `DECISIONS.md`:
current state, evidence, non-negotiables, stop states, owner decisions, and next
safe action.

## Hard Stops

Stop on disallowed paths, overlapping dirty state, missing task card, failed
validation, missing owner approval for GitHub writes, product/runtime/data or
extraction boundary crossings, cleanup requests, or `DATA_MISSING` that would
make mutation unsafe.
