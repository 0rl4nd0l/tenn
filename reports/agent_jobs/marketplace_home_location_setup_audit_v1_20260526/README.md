# Marketplace Home Location Setup Audit

## Summary

Issue #117 asked whether `No home location saved` blocks Marketplace mission
quality or leaves the user without a setup path. Current evidence shows the
state is informational, not a confirmed product gap: Settings has a saved home
location input, the assistant asks for location when no default exists, mission
drafts require location before creation, and backend mission creation also
requires explicit location scope.

## Decision

- Close gate: `COMPLETED_WITH_EVIDENCE`
- Finding class: `NO_FOLLOWUP`
- Product remediation landed: NO. This was an audit issue.
- Follow-up required: NO

## Evidence

| Area | Current evidence | Result |
| --- | --- | --- |
| Saved setup path | `cockpit-ui/components/cockpit/settings/settings-screen.tsx:518` exposes Marketplace Preferences with a `Home location / suburb` input, and `settings-screen.test.tsx:31` verifies saving it to preferences. | PASS |
| Assistant first-run prompt | `cockpit-ui/lib/marketplace-assistant.ts:578` greets with the saved location when present and asks for location when none is saved. | PASS |
| Draft behavior | `marketplace-assistant.ts:585` creates drafts with saved location if present; `:630` requires missing `location`; `:749` fills a saved home location when merging. | PASS |
| UI disclosure | `marketplace-assistant.tsx:344` displays either the saved location or `No home location saved`, and `:459` shows missing fields. | PASS |
| Backend guard | `test_marketplace_mission_service.py:612` requires explicit location scope; `:626` verifies canonicalized Victoria location. | PASS |
| Search builder | `test_marketplace_search_builder.py:9` and `:179` verify location names and preferred suburbs enter query packs. | PASS |

## Boundary Compliance

- No production DB/Qdrant/news/memory mutation.
- No preference or storage schema mutation.
- No canonical financial truth mutation.
- No parser routing, extraction prompt, or gold-label mutation.
- No runtime/model/GPU/service config mutation.
- No product code changed.

## Validation Notes

Focused backend Marketplace tests passed using the existing main-checkout venv
with `PYTHONPATH` pointed at this isolated worktree. Local Vitest tests could
not be run because `vitest` is absent in the isolated worktree; the frontend
test files were inspected instead.
