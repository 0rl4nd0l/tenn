---
job_id: cockpit_accessible_controls_marketplace_mission_v1_20260602
lane: Reporting
supporting_lanes:
  - Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_accessible_controls_marketplace_mission_v1_20260602.md
  - reports/agent_jobs/cockpit_accessible_controls_marketplace_mission_v1_20260602/README.md
  - reports/agent_jobs/cockpit_accessible_controls_marketplace_mission_v1_20260602/status.json
  - reports/agent_jobs/cockpit_accessible_controls_marketplace_mission_v1_20260602/validation.json
  - reports/agent_jobs/cockpit_accessible_controls_marketplace_mission_v1_20260602/diff-check.json
  - cockpit-ui/components/cockpit/marketplace/mission-screen.tsx
  - cockpit-ui/components/cockpit/marketplace/mission-screen.test.tsx
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_accessible_controls_marketplace_mission_v1_20260602
mutation_mode: safe_extension
production_data_access: false
allowed_github_mutation:
  - "read issue #53 and adjacent accessible-control pull requests"
  - "open one pull request referencing issue #53 after validation passes"
---

# Cockpit Marketplace Mission Accessible Controls

## Objective

Add durable accessible names to Marketplace mission creation controls that
currently rely on visible text without programmatic label association or on
placeholder-only lookup in tests.

This is a narrow remediation slice for issue #53. It does not close #53 by
itself.

## Target Issue

- #53 `Production Cockpit forms rely on placeholders and unlabeled icon controls`

## Current Evidence

Current repo inspection found the Marketplace mission creation form renders
visible labels adjacent to inputs, but the labels are not programmatically
associated with the controls:

- `cockpit-ui/components/cockpit/marketplace/mission-screen.tsx` mission name
  input relies on placeholder text in the current focused test.
- The max price and scan cadence number inputs have visible text labels but no
  `htmlFor`/`id` association.
- The search brief text area and CSV keyword/location inputs have visible text
  labels but no `htmlFor`/`id` association.
- The existing mission creation test still queries those controls by
  placeholder text, which does not prove durable accessible role/name behavior.

Duplicate and overlap checks found existing #53 remediation PRs for
chat/holdings, memory/updater, verification header, news/history, Marketplace
assistant, Intel Ops, and Thesis Audit controls. Operations is covered by an
open PR that touches `operations-screen.tsx`. Marketplace alerts and matches
are touched by an open empty-state PR. No current PR found for
`mission-screen.tsx` mission creation accessible-name wiring.

## Safe Extension Scope

- Programmatically associate the existing visible Marketplace mission creation
  labels with their form controls.
- Preserve the existing visual layout, form state, payload construction, API
  calls, backend ownership, and Marketplace mission semantics.
- Update focused tests to query mission creation controls by role/name instead
  of placeholder text.

## Forbidden

- Backend, runtime, memory-store, extraction, parser, prompt, source-label,
  gold-label, GPU, service-config, Qdrant, Postgres, or production-data changes.
- Marketplace ingestion, scan, ranking, pricing, alert, match, capture-token,
  or persistence semantics.
- Broad UI redesign, navigation changes, or unrelated accessibility slices.
- Unrelated dirty-work cleanup.

## Validation

- Task-card validate/check-overlap/claim/check-diff/release.
- Focused Vitest for Marketplace mission controls.
- Targeted ESLint for touched Marketplace mission files.
- Cockpit UI TypeScript `tsc --noEmit`.
- `git diff --check` and `git diff --cached --check`.

## Definition of Done

- Marketplace mission name, max price, scan cadence, brief, include keywords,
  exclude keywords, preferred brands, and locations controls can be selected by
  durable accessible role/name queries.
- Existing mission creation payload behavior still passes focused tests.
- No forbidden surfaces are touched.
- PR references #53 and clearly states this is a partial remediation slice.
