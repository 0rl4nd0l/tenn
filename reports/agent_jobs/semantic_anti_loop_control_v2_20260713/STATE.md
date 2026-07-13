# State

Status: implementation and local validation complete; publication pending

## Scope

- Repository: Tenn control plane
- Branch: `control-plane/semantic-anti-loop-v2-20260713`
- Verified base at start: `871c8566d05c318a7089e496eb2190287a21db06`
- Target transition: `merged_v2_semantic_anti_loop_control`
- Runtime, model, database, service, timer, and production-data mutation: none

## Implemented Control

- V1 task cards remain valid and emit migration warnings.
- V2 cards declare semantic scope, program track, evidence identity,
  transition, capabilities, and reopen conditions.
- Scope fingerprints are computed from normalized semantic fields.
- Decision state is append-only and separate from task state.
- Portable preflight classifies resolved reuse, active duplicates, no-delta
  loops, changed evidence, new hypotheses, and transition-specific blockers.
- V2 closeout requires `RUN_OUTCOME.json`, declared capability use, a real
  decision delta for `ADVANCED`, and conditional continuation goals.
- V2 board decisions and run outcomes must agree.

## Review State

Two integrated reviews found fail-open version parsing, stale-decision
precedence, cross-track leakage, registry-path divergence, non-canonical hash
representations, weak delta typing, V1-board acceptance in V2 closeout,
nonzero-exit gaps, corrupt-registry handling, stale evidence-pair leakage, and
missing durable closeout binding. The code-fixer passes repaired every finding
with focused regressions. A final bounded post-fix review reported no critical,
warning, or suggestion findings.

## Boundaries Preserved

- No product or runtime code was changed.
- No database, model, timer, service, or deployment state was changed.
- No registry pointer was changed.
- The Greyhound launch checkout was not modified.
- No `NEXT_GOAL.md` is created for this advanced run because a separate
  continuation goal is not required by this closeout.
