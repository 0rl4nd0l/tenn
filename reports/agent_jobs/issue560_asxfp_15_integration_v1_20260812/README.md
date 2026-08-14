# Issue #560 ASXFP 05–15 integration

## Identity and scope

- Exact accepted input from Issue #559: `2c21773b79dffb1399b2eba1da006f53695bf90b`.
- Input tree: `6486ac8aad3b91fa91dedcdef771fcc96cc738fe`.
- Integration branch: `codex-x/20260812T062313Z-38b8b6f405-1613cb`.
- Ticket 14 implementation commit: `414c7921`.
- Ticket 15 implementation commit: `9db0275e`.
- Post-review currency repair commit: `6782e890`.
- The immutable accepted carry-forward SHA and tree are reported in the session handoff because a tracked file cannot contain its own commit identity.

The live Issue #560, canonical recovery programme, PRs #541–#542, checks,
candidate commits, worktrees, and ownership were refreshed before implementation.
Only the launcher-owned integration worktree was present. PR #541 and PR #542
remained open drafts with green historical `lint-and-test` and `scan` checks and
clean merge states; those workflow facts were treated as evidence, not acceptance.

## Red loops and behavior

Ticket 14 began at the public multipass result/validation seam. Three production-
shaped tests failed because missing and string-null currency were rewritten to AUD.
The repair preserves explicit native currency without FX conversion and fails closed
when currency is missing or null-like.

Spec review then found that unequal or tied mixed table currencies could still select
a winner or fall back to classifier currency, and that `none`, `n/a`, `unknown`, and
`-` could pass as native currency. Five focused tests established the red loop. The
post-review repair treats any mixed explicit statement-table currencies as conflict,
clears classifier fallback, and normalizes all supported null-like forms to unknown.

Ticket 15 began at the accepted-observation compatibility projection and production-
reader seams. Seven financial-observation tests failed before the production carry-
forward. The repair makes active accepted statutory observations the sole financial
truth authority, deterministically projects compatibility-shaped rows, keeps synthetic
confidence null, and retires remaining direct legacy reads and writes while preserving
truthful compatibility exports.

## Validation

- Complete multipass extraction file: `321 passed`.
- Remaining changed Ticket 15 files: `380 passed, 2 skipped`.
- Standalone cockpit compatibility script: `3 passed`.
- Combined Ticket 15 run before review repair: `696 passed, 2 skipped`, plus `3 passed` standalone.
- Repository-wide backend run completed: `2503 passed, 18 skipped, 1 deselected, 48 failed`.
- The 48 residual failures were outside the ASXFP 05–15 changed seams: missing optional
  `yt_dlp` and Playwright packages/browser runtime, and route-profile inventory tests
  degraded by unavailable optional application imports. Focused reruns reproduced those
  environment/profile failures. No failing test exercised a changed 05–15 behavior.
- Ruff on every changed Python file: passed.
- Python compilation on every changed Python file: passed.
- `git diff 2c21773b79dffb1399b2eba1da006f53695bf90b...HEAD --check`: passed.
- No database migration, extraction, OCR, model, service, queue, cache, runtime/data,
  protected-data, source-document, or canonical-fact write was executed.

## Review and residual risk

Standards review found no documented-standard violation or blocker. It deferred two
low-priority structural improvements: replace positional projection-truth tuples with a
named domain type, and centralize adapters around untyped compatibility projection rows.

Initial Spec review found the two currency blockers described above. Re-review at
`6782e890` confirmed both resolved and found no remaining code/spec blocker or scope
creep. The repository-wide optional-dependency/profile failures remain validation noise;
the highest available no-write ASXFP integration seams are green and independently
exercise the Issue #560 acceptance behavior.

## Recoverability and Ticket 16 handoff

The three implementation commits are independently revertible. Historical PRs #541 and
#542 and their exact candidates remain recovery pointers; no branch or artifact cleanup
occurred. Ticket 16 / Issue #561 must start from the exact final Issue #560 SHA reported
in the handoff, then refresh canonical authority, B8 `88ba2882dce88ab091b67128a4a96674ad8b79bd`,
B9 `ae86a9990836a919debe8fb10d5fc7417d29089f`, the failed B6 release candidate
`4206e6d1d850598628405f0282f6e38b2f5ad012`, current PRs/checks, ownership, and
worktrees before diagnostic-only comparison.

No push, merge, rebase, GitHub mutation, deployment, protected evaluation, runtime/data
mutation, cleanup, deletion, closure, or registry release occurred.
