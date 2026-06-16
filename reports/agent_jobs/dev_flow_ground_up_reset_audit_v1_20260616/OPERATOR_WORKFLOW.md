# Operator Workflow

## When Something Is Broken

Use `/issue`.

Expected behavior:

- ask at most one or two clarifying questions if needed;
- run Git guard preflight;
- inspect current issue/PR/report evidence;
- invoke the `diagnose` loop only when a reproducible bug or performance
  regression is actually in scope;
- produce `ISSUE.md`, `MILESTONES.md`, context pack, and `NEXT_GOAL.md`.

## When Orlando Wants An Explanation

Use `/explain`.

It should explain:

- what the thing is;
- why it exists;
- current state;
- risks;
- what changed;
- what is still broken;
- what Orlando should do next.

It should write `EXPLAIN.md` when the topic is non-trivial or likely to be
reused.

## When Orlando Wants Implementation

Use `/fix`.

Expected behavior:

- read issue/board decision;
- run Git guard;
- create or validate a task card;
- spawn bounded workers only when useful;
- integrate one coherent change;
- run focused validation;
- run code review;
- prepare PR only with approval.

## Before Risky Merges

Use `/review-board`, then `code-reviewer`.

`/review-board` should produce `BOARD.md`, `BOARD_DECISION.json`, and
`NEXT_GOAL.md`. It must end with a decision: merge, fix first, park, supersede,
or block.

## Repo Hygiene

Do not run cleanup by default. Git Hygiene should happen automatically inside
every command. Invoke a full hygiene audit only when Orlando explicitly wants a
fleet/branch/worktree cleanup plan.

## What Requires Owner Approval

- GitHub writes;
- commits, pushes, PR creation, merge, rebase, cherry-pick;
- branch deletion, worktree removal, prune, stash, reset, clean;
- product/runtime/data/extraction mutation;
- DB/Qdrant/Redis/news/memory/source-PDF/gold-label/model/GPU/service changes;
- broad dependency, CI, or hook behavior changes.

## Avoiding Report-Only Loops

Every report-only command must end with one of:

- execute next safe task;
- ask for a specific approval;
- park with an owner decision;
- close as no-op with evidence;
- create one concrete next goal.

Do not create another report whose only output is "run another report".

## Avoiding Dirty Worktree Sprawl

- one worker, one worktree, one lane, one result file;
- no worker leaves unreported dirt;
- workers never share a mutation surface;
- all worker output goes into `WORKER_RESULT.md`;
- orchestrator integrates or parks worker output before ending.
