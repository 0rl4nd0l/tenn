# Cockpit Marketplace Mission Accessible Controls

Job: `cockpit_accessible_controls_marketplace_mission_v1_20260602`

Lane: Reporting

Mode: safe extension

Issue: #53

## Scope

This report tracks a narrow Marketplace mission creation accessibility slice:
programmatically associate existing visible labels with mission creation form
controls, then prove the controls through role/name tests.

## Result

Implemented and ready for PR.

- Added programmatic `htmlFor`/`id` label associations for the Marketplace
  mission creation form.
- Updated the focused mission creation test to query controls by role/name
  rather than placeholder text.
- Preserved existing mission creation payload behavior.

## Validation

- Task-card validate/check-overlap/claim passed.
- Focused Marketplace mission Vitest passed: 1 file, 14 tests.
- Targeted ESLint exited successfully with one existing `no-img-element`
  warning in `mission-screen.tsx`.
- Cockpit UI TypeScript `tsc --noEmit` passed.
- Task-card `check-diff` passed.
- `git diff --check` passed.
