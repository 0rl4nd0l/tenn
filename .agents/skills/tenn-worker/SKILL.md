---
name: tenn-worker
description: Tenn bounded worker contract for subagents used by tenn-fix. One worker, one lane, one worktree, one result file, no invisible dirt.
---

# Tenn Worker

Use `tenn-worker` only when an orchestrator assigns a bounded unit of work.

One worker gets one lane, one worktree, one brief, and one result file. Workers
must not share a mutation surface.
`WORKER_RESULT.md` is mandatory.

## Required Contract

The worker brief must include:

- objective
- lane
- worktree path
- branch
- task card
- exact allowed files
- validation expected
- stop conditions
- result path for `WORKER_RESULT.md`
- parent task id
- Task Ledger expectations: child ledger entry or required ledger fields in
  `WORKER_RESULT.md`
- task tier and model routing fields:
  - `task_tier`
  - `recommended_model`
  - `actual_model`
  - `why_this_model`
  - `worker_model_allowed`
  - `worker_decision_limit`
  - `escalation_needed`

## Model And Decision Contract

Workers are Codex development-tooling helpers. They should not turn project
workflows into Tenn-specific runtime machinery unless the assigned task depends
on this repo's task-card registry, owner-boundary rules, extraction boundaries,
or financial-truth safety constraints.

Task tiers:

- `small`: grep/search, JSON parse, file listing, report summarization, simple
  docs update, focused test run. Recommended model: mini/low-cost.
- `medium`: small bug fix, one/two-file code change, targeted regression, PR
  comment fix. Recommended model: standard coding model.
- `large`: multi-file correctness, schema/persistence, architecture change, or
  tricky debugging. Recommended model: high reasoning.
- `critical`: DB/runtime mutation, destructive Git, financial truth, merge
  conflict, high-risk cleanup, or owner-boundary decision. Recommended model:
  high reasoning plus review-board.

Allowed worker decision limits:

- `evidence_only`: gather facts and report uncertainty.
- `recommendation_only`: propose a plan; do not mutate or decide.
- `bounded_implementation`: implement only the exact assigned lane and files.

Small/cheap workers are appropriate for bounded evidence gathering. Small models
must not make final decisions on high-risk work. Escalate architecture, schema,
financial truth, merge readiness, destructive operations, and owner-boundary
decisions back to the orchestrator or review board.

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

## Required Behavior

1. Run `tenn-git-guard` in the assigned worktree.
2. Confirm the task card and allowed files before mutation.
3. Write a child ledger entry when the brief provides an approved ledger write
   path, or include ledger fields in `WORKER_RESULT.md` when ledger writes are
   unavailable.
4. Work only inside assigned scope.
5. Run focused validation if mutation occurred.
6. Leave no invisible dirt. Every changed, untracked, generated, ignored, or
   skipped file must be reported.
7. Respect `worker_decision_limit`; stop instead of widening scope or making a
   decision above the assigned tier.

## Output

Write `WORKER_RESULT.md` with:

- branch
- worktree
- parent task id
- worker id
- lane
- task tier
- recommended model
- actual model
- why this model
- worker model allowed
- worker decision limit
- escalation needed
- ledger status or `DATA_MISSING`
- task status
- files changed
- touched files
- tests or checks run
- result path
- risks
- blockers and `DATA_MISSING`
- recommended action

The orchestrator decides whether to integrate, park, or discard worker output.
The worker must not push, merge, rebase, delete, clean, or mutate GitHub unless
the brief explicitly allows that exact action.

If the worker cannot finish inside its lane, it must stop with blockers and
leave all dirt visible in `WORKER_RESULT.md`.
