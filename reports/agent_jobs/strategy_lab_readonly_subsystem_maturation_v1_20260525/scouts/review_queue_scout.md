# Review Queue Scout

Mode: audit-only internal pass.

## Confirmed

- Existing Cockpit Strategy Lab artifacts route is repo-backed and read-only.
- Existing artifact review source model already distinguishes authoritative
  `strategy_lab_artifact_v1`, helper pre-envelope evidence, and report evidence.
- A queue layer can be derived from repo paths without DB persistence.

## Inferred

- Queue items should group by analyst review concern rather than by file type:
  repeatability, transport contract, runtime proof, degraded state,
  cleanup/revoke, review decisions, promotion blockers, and unresolved risks.
- `priority_then_sort_key` is sufficient for first-pass ergonomics because this
  is not a mutable queue.

## DATA_MISSING

- Human review owner.
- Review decision timestamp.
- Any mutable review-state store.

## Chosen Implementation

Add static repo-backed queue metadata and file availability to the existing
artifact route. Keep queue state read-only and derive all missing items as
`DATA_MISSING`.
