# Cockpit Intel Ops Accessible Controls

## Summary

Partial remediation for issue #53. This slice adds durable accessible names to
Intel Ops controls without changing data fetching, Intel Pulse semantics,
diagnostic matrix semantics, or backend/runtime behavior.

## Changes

- Added a programmatic name to the Intel Ops company scope search input.
- Added a programmatic name to the icon-only clear-scope button.
- Added action-specific programmatic names to pipeline stage buttons.
- Added action-specific programmatic names to diagnostic matrix cell buttons.
- Added action-specific programmatic names to failure registry row buttons and
  the disabled read-only retry control.
- Added focused component tests that query these controls by role/name and
  verify existing callbacks still fire.

## Boundaries

No backend, extraction, retrieval, memory, financial truth, source/evidence
label, Qdrant/Postgres, runtime/model/GPU, service-config, parser, prompt, or
gold-label behavior changed.

## Validation

- Task card validate: pass.
- Registry check-overlap: pass.
- Registry claim: pass.
- Focused Vitest: `components/intel-ops/intel-ops-accessibility.test.tsx`, 4
  tests passed.
- Targeted ESLint: touched Intel Ops components and test passed.
- Cockpit UI TypeScript: `tsc --noEmit --pretty false` passed.

## Notes

This keeps #53 open for the broader route-level accessibility sweep.
