# Subagent Delegation Design

## Goal

Use subagents to reduce risk and context load, not to create invisible parallel
mutation.

## When To Delegate

Delegate only when at least one is true:

- evidence gathering can be split into independent lanes
- a skeptic/reviewer pass would materially reduce risk
- a worker can operate in a separate worktree with exact allowed files
- a large problem needs strategy bids before implementation
- a domain specialist can inspect a bounded artifact set faster than the main
  agent

Do not delegate for trivial edits, single-file docs changes, one command output,
or contested mutation surfaces.

## Worker Contract Additions

Extend `WORKER_RESULT.md` and worker briefs with:

```yaml
task_tier: small | medium | large | critical
model_tier: mini | standard | high_reasoning
decision_limit: evidence_only | recommendation_only | bounded_implementation
worktree: <path>
branch: <branch>
result_file: <path>
allowed_files:
  - <path>
must_not_touch:
  - <path or surface>
```

## Strategy-Bid Stage

For `large` and `critical` tasks:

1. Run two or three short read-only strategy bids.
2. Each bid must include evidence inspected, plan, validation, risks, and stop
   states.
3. The orchestrator chooses one plan or synthesizes a bounded hybrid.
4. The choice is recorded in `DECISIONS.md` or `BOARD_DECISION.json`.

Small workers may propose plans. They may not approve final high-risk actions.

## Safe Worker Patterns

| Pattern | Use | Rule |
| --- | --- | --- |
| Evidence scout | Search files/reports/issues. | Read-only; write only result file. |
| Validation scout | Run focused tests/checks. | No source edits; raw logs in report path. |
| Review scout | Check diff against task-card/risk. | Read-only; no fixes. |
| Implementation worker | Apply one bounded change. | Separate worktree, exact allowlist, result file. |
| Strategy bidder | Propose short plan. | No edits; no final decision. |

## Unsafe Worker Patterns

- Multiple writers in one worktree.
- Workers sharing a mutable file.
- Workers deciding merge/destructive/Financial Truth outcomes.
- Workers without result files.
- Workers that hide untracked, ignored, generated, or skipped files.
- Workers that bypass task-card validation because the parent already did it.

## Required Closeout Fields

Every parent report using subagents must list:

- workers launched
- model tier per worker
- lane and worktree per worker
- result file per worker
- files inspected or changed
- validation each worker ran
- final orchestrator decision
- discarded worker output and why
