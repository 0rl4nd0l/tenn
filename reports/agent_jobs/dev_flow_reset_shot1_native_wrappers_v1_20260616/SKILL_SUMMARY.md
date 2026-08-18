# Skill Summary

## Canonical Flow

`/issue -> /review-board -> /fix`

Git Hygiene is represented by `tenn-git-guard`, a backend guard that each
workflow calls before current-state claims or mutation.

## Wrappers

- `tenn-issue`: frames vague owner problems, runs Git guard, invokes existing
  `diagnose` only when debugging/repro is needed, ranks candidates using
  `tenn-auto-progress` ideas, and writes issue artifacts.
- `tenn-review-board`: runs independent perspectives and writes a required
  decision artifact.
- `tenn-fix`: orchestrates bounded implementation from issue/board/task-card
  inputs, validates scope, integrates one coherent change, runs focused
  validation, and uses code review.
- `tenn-worker`: defines the bounded worker contract: one worker, one lane, one
  worktree, one result file.
- `tenn-explain`: produces layman-depth but evidence-grounded explanations.
- `tenn-code-reviewer`: wraps host `code-reviewer` as a Tenn final review gate.
- `tenn-improve-codebase-architecture`: wraps host architecture improvement
  analysis with Tenn report-only defaults and execution gates.
- `tenn-git-guard`: wraps Git Hygiene as a quiet native backend preflight.

## Preserved Existing Skills

Existing repo skills were not removed or renamed. Existing host `diagnose` is
preserved and referenced as a debugging loop used by `tenn-issue`.
