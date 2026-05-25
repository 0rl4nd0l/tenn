# Validation Regression Scout

Mode: audit-only internal pass.

## Confirmed

- Focused Strategy Lab Vitest and Python unittest paths already exist.
- Existing validation checks assert read-only flags, no real transport, no store
  writes, and `current_sidecar_available=false`.

## Inferred

- New regression coverage should parse docs/packets and grep for forbidden
  promotion values rather than relying only on UI text.

## DATA_MISSING

- Browser smoke result for this task until validation runs.
- Final TypeScript, ESLint, JSON validation, secret scan, forbidden-promotion
  grep, and task-card diff-check until closeout.

## Chosen Implementation

Add a focused Python regression file plus expanded Vitest coverage for queue,
session, and packet workflow semantics.
