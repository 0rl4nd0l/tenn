---
job_id: cockpit_accessible_controls_intel_ops_v1_20260602
lane: Reporting
supporting_lanes:
  - Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_accessible_controls_intel_ops_v1_20260602.md
  - reports/agent_jobs/cockpit_accessible_controls_intel_ops_v1_20260602/README.md
  - reports/agent_jobs/cockpit_accessible_controls_intel_ops_v1_20260602/status.json
  - reports/agent_jobs/cockpit_accessible_controls_intel_ops_v1_20260602/validation.json
  - reports/agent_jobs/cockpit_accessible_controls_intel_ops_v1_20260602/diff-check.json
  - cockpit-ui/components/intel-ops/scope-terminal.tsx
  - cockpit-ui/components/intel-ops/pipeline-ribbon.tsx
  - cockpit-ui/components/intel-ops/diagnostic-matrix.tsx
  - cockpit-ui/components/intel-ops/failure-registry.tsx
  - cockpit-ui/components/intel-ops/intel-ops-accessibility.test.tsx
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_accessible_controls_intel_ops_v1_20260602
mutation_mode: safe_extension
production_data_access: false
allowed_github_mutation:
  - "read issue #53 and adjacent accessible-control pull requests"
  - "open one pull request referencing issue #53 after validation passes"
---

# Cockpit Intel Ops Accessible Controls

## Objective

Add durable accessible names to the Intel Ops controls that still rely on
placeholder text, icon-only buttons, dense matrix cells, or composite row text
for their programmatic names.

This is a narrow remediation slice for issue #53. It does not close #53 by
itself.

## Target Issue

- #53 `Production Cockpit forms rely on placeholders and unlabeled icon controls`

## Current Evidence

Current repo inspection found Intel Ops controls without explicit durable
programmatic names:

- `cockpit-ui/components/intel-ops/scope-terminal.tsx` company search input
  uses placeholder text as its only visible affordance.
- `cockpit-ui/components/intel-ops/scope-terminal.tsx` clear-company button is
  icon-only.
- `cockpit-ui/components/intel-ops/pipeline-ribbon.tsx` stage buttons are dense
  compact controls without action-specific accessible names.
- `cockpit-ui/components/intel-ops/diagnostic-matrix.tsx` matrix-cell buttons
  are color-only controls.
- `cockpit-ui/components/intel-ops/failure-registry.tsx` failure row buttons
  rely on composite row text rather than an action-specific control name.

Duplicate checks found existing narrow #53 remediation PRs for chat/holdings,
memory/updater, verification, news/history, and Marketplace assistant controls,
but no PR or issue for Intel Ops accessible controls.

## Safe Extension Scope

- Add `aria-label` or equivalent programmatic names to existing Intel Ops
  controls.
- Preserve visual text, layout, event handlers, polling, API calls, and backend
  data semantics.
- Add focused component tests that query controls by role/name and verify the
  existing handlers still fire.

## Forbidden

- Backend, runtime, memory, extraction, parser, prompt, source-label, gold-label,
  GPU, service-config, Qdrant, Postgres, or production-data changes.
- Intel Pulse, diagnostic matrix, failure registry, or financial-truth semantic
  changes.
- Broad UI redesign, navigation changes, or unrelated accessibility slices.
- Unrelated dirty-work cleanup.

## Validation

- Task-card validate/check-overlap/claim/check-diff/release.
- Focused Vitest for Intel Ops accessible controls.
- Targeted ESLint for touched Intel Ops components and test.
- Cockpit UI TypeScript `tsc --noEmit`.
- `git diff --check` and `git diff --cached --check`.

## Definition of Done

- Intel Ops search, clear, stage, matrix-cell, and failure-row controls can be
  selected by durable accessible role/name queries.
- Existing callbacks still fire in focused tests.
- No forbidden surfaces are touched.
- PR references #53 and clearly states this is a partial remediation slice.
