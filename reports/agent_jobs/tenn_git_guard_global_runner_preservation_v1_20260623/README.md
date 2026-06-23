# Tenn Git Guard Global Runner Preservation

timestamp: 2026-06-23T17:59:11+1000

## Summary

Implemented the repo-backed preservation lane for `tenn-git-guard`:

- updated `.agents/skills/tenn-git-guard/SKILL.md` to prefer the portable runner before repo-local scripts;
- added the portable runner and tests under `.agents/skills/tenn-git-guard/scripts/` and `.agents/skills/tenn-git-guard/tests/`;
- updated `docs/dev_flow/SKILLS_SURFACE.md` so future agents do not treat missing runtime repo-local Tenn scripts as corruption;
- wrote guard-smoke evidence for this control-plane worktree and the Greyhound runtime checkout.

The Greyhound runtime guard result is now the intended shape:

- `guard_support_status=PASS`
- `registry_status=PASS`
- `ledger_status=DATA_MISSING`
- `data_missing_sources=["ledger:committed", "ledger:live"]`
- `final_decision=warning`

This means guard support is fixed; missing runtime ledger rows remain missing
until ledger state itself is populated.

## Preservation State

The preservation worktree was normalized onto
`control-plane/tenn-git-guard-global-runner-preservation-v1-20260623` from
current `origin/migration/clean-runtime-baseline-reconstruct-v1` before
commit/push. The staged preservation surface is limited to the task card,
repo-backed guard skill, guard runner/tests, skill-surface docs, and report
artifacts listed by the task card.

No registry mutation, DB mutation, runtime service mutation, training,
promotion, EV, betting, snapshot rewrite, or gate weakening was performed.

## Artifacts

- `GUARD_SMOKE.json`: repo-backed guard preflight for this control-plane worktree.
- `RUNTIME_GUARD_SMOKE.json`: repo-backed guard preflight for the Greyhound runtime checkout.
- `RUNTIME_DIRTY_CLASSIFICATION.md`: Greyhound runtime dirt buckets.
- `VALIDATION.md`: validation commands and results.
- `handoff/HANDOFF.md`: closeout handoff for the preservation lane.
- `handoff/NEXT_GOAL.md`: no-runtime-mutation continuation prompt.
- `handoff/LEDGER_ENTRY.json`: report-local ledger entry because no live ledger mutation was authorized.

## Promotion State

Greyhound promotion remains blocked. The next runtime lane must still prove a
completed full daemon child with non-empty predictions/unified evidence, 100+
safe eligible races, and passing identity, source, official-result, and pre-jump
timing gates.
