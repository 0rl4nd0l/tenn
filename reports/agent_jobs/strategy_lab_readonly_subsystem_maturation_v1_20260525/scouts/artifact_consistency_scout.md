# Artifact Consistency Scout

Mode: audit-only internal pass.

## Confirmed

- `strategy_lab_artifact_v1` remains authoritative.
- Helper and report evidence remain non-authoritative unless mapped through the
  authoritative envelope.
- Clean re-probe evidence is report evidence, not canonical Tenn financial
  truth.

## Inferred

- The session envelope should reference runtime, reprobe, degraded-state,
  cleanup, revoke, and review/export packet refs separately so missing evidence
  is visible by category.

## DATA_MISSING

- Full source commit ref for the Tenn checkout that produced clean re-probe
  evidence.
- Runtime adapter review.
- Human artifact-review decision.

## Chosen Implementation

Add experiment-session and packet schemas plus a focused regression test that
checks all new docs/packets preserve non-live and non-canonical flags.
