# Provenance UX Scout

Mode: audit-only internal pass.

## Confirmed

- The current Strategy Lab UI already renders source paths, report paths,
  historical status, and `DATA_MISSING`.
- The clean re-probe evidence includes status, runtime proof, cleanup proof,
  no-mutation attestation, sanitized payloads, revoke proof, and zero-order
  proof.

## Inferred

- Analyst review improves if Cockpit shows one experiment session envelope
  instead of only a flat artifact list.
- Export packets give reviewers durable context outside the browser without
  adding an artifact store.

## DATA_MISSING

- No human review decision packet exists.
- No final commit ref exists until this task is committed.

## Chosen Implementation

Show review queue, experiment session, and export packets in the existing
Strategy Lab artifact review card. Preserve source paths and provenance labels.
