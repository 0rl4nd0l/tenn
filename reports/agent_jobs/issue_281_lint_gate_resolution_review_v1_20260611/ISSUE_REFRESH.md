# Issue Refresh

Issue: https://github.com/0rl4nd0l/tenn/issues/281

Title: `[Evaluation] Add lint/type gates for financial-engine_v2 backend and scripts`

State: OPEN

Labels:

- `lane:evaluation`
- `lane:repo-hygiene`
- `priority:p2`
- `risk:medium`
- `state:ready`
- `type:validation-gap`

Milestone: none.

## Body Summary

Problem: Python tests pass, but backend/scripts lack lint or type gate coverage.

Suggested fix: add a minimal lint gate, preferably Ruff, scoped to
`financial-engine_v2/backend` and `financial-engine_v2/scripts`; optionally add
a light type/import check later.

Acceptance criteria:

- documented command exists for linting active Python code
- CI or local scripts can run it without external services
- intentional generated/legacy paths are excluded or configured

## Comment Evidence

One owner comment from 2026-06-03 says PR #289 was merged into
`tmp/sloppy-fix-demo` as merge commit `2a62a751`, and that #281 remained open
because Python Ruff/type gates for backend and scripts were not yet configured.

## Search Evidence

- Open PR search for `ruff lint type gate 281`: no open PRs returned.
- Closed PR search for `ruff lint type gate 281`: no closed PRs returned.
- Issue search for `ruff lint type gate`: #281 returned, plus adjacent unrelated
  validation-gap issues.

## Current Interpretation

The GitHub issue remains open and stale relative to the current checkout. The
body makes type/import checking optional; the minimum Ruff lint-gate criteria
appear satisfied in current repo evidence.
