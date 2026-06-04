# Cockpit Thesis Audit Accessible Controls

## Summary

Partial remediation for issue #53. This slice adds durable accessible names to
Thesis Audit controls without changing API calls, thesis audit semantics, memory
proposal gating, or backend/runtime behavior.

## Changes

- Added programmatic names to the ticker, focus, report-upload, and report-text
  inputs.
- Added an action-specific programmatic name to the coverage refresh icon
  button.
- Added target-specific names to proposal staging, past-audit deletion, and
  watchdog alert dismissal controls.
- Added `type="button"` to the watchdog alert dismiss button.
- Fixed two touched-file lint issues while validating the component.
- Added focused component tests that query these controls by role/name and
  verify core callbacks still fire.

## Boundaries

No backend, extraction, retrieval, memory-store, financial truth,
source/evidence label, Qdrant/Postgres, runtime/model/GPU, service-config,
parser, prompt, or gold-label behavior changed.

## Validation

- Task card validate: pass.
- Registry check-overlap: pass.
- Registry claim: pass.
- Focused Vitest: `components/cockpit/thesis-audit/thesis-audit-screen.test.tsx`,
  3 tests passed.
- Targeted ESLint: touched Thesis Audit component and test passed.
- Cockpit UI TypeScript: `tsc --noEmit --pretty false` passed.

## Notes

This keeps #53 open for the broader route-level accessibility sweep.
