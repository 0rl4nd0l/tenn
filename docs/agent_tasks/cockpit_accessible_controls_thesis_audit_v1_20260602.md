---
job_id: cockpit_accessible_controls_thesis_audit_v1_20260602
lane: Reporting
supporting_lanes:
  - Evaluation
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_accessible_controls_thesis_audit_v1_20260602.md
  - reports/agent_jobs/cockpit_accessible_controls_thesis_audit_v1_20260602/README.md
  - reports/agent_jobs/cockpit_accessible_controls_thesis_audit_v1_20260602/status.json
  - reports/agent_jobs/cockpit_accessible_controls_thesis_audit_v1_20260602/validation.json
  - reports/agent_jobs/cockpit_accessible_controls_thesis_audit_v1_20260602/diff-check.json
  - cockpit-ui/components/cockpit/thesis-audit/thesis-audit-screen.tsx
  - cockpit-ui/components/cockpit/thesis-audit/thesis-audit-screen.test.tsx
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_accessible_controls_thesis_audit_v1_20260602
mutation_mode: safe_extension
production_data_access: false
allowed_github_mutation:
  - "read issue #53 and adjacent accessible-control pull requests"
  - "open one pull request referencing issue #53 after validation passes"
---

# Cockpit Thesis Audit Accessible Controls

## Objective

Add durable accessible names to Thesis Audit controls that currently rely on
placeholder text, generic icon-only labels, or title-only buttons.

This is a narrow remediation slice for issue #53. It does not close #53 by
itself.

## Target Issue

- #53 `Production Cockpit forms rely on placeholders and unlabeled icon controls`

## Current Evidence

Current repo inspection found Thesis Audit controls with weak programmatic names:

- `cockpit-ui/components/cockpit/thesis-audit/thesis-audit-screen.tsx` ticker
  and focus inputs use placeholder-only naming.
- The source report file input is visually represented by the surrounding
  label and mutable filename text.
- The report text area uses placeholder-only naming.
- The coverage refresh icon button uses a `title` but no durable action label.
- Past audit deletion uses a generic `Remove` label.
- Watchdog alert dismissal uses a `title` but no button type or durable action
  label.
- Thesis memory proposal staging buttons share the visible text `Stage`.

Duplicate checks found existing narrow #53 remediation PRs for chat/holdings,
memory/updater, verification, news/history, Marketplace assistant, and Intel
Ops controls, but no PR or issue for Thesis Audit accessible controls.

## Safe Extension Scope

- Add `aria-label` or equivalent programmatic names to existing Thesis Audit
  controls.
- Preserve visual text, layout, event handlers, API calls, backend ownership,
  memory confirmation behavior, and thesis audit semantics.
- Add focused component tests that query controls by role/name.

## Forbidden

- Backend, runtime, memory-store, extraction, parser, prompt, source-label,
  gold-label, GPU, service-config, Qdrant, Postgres, or production-data changes.
- User thesis memory semantics, proposal gating, audit/coverage endpoint
  behavior, or financial-truth changes.
- Broad UI redesign, navigation changes, or unrelated accessibility slices.
- Unrelated dirty-work cleanup.

## Validation

- Task-card validate/check-overlap/claim/check-diff/release.
- Focused Vitest for Thesis Audit accessible controls.
- Targeted ESLint for touched Thesis Audit files.
- Cockpit UI TypeScript `tsc --noEmit`.
- `git diff --check` and `git diff --cached --check`.

## Definition of Done

- Thesis Audit ticker, focus, report upload, report text, coverage refresh,
  proposal stage, history delete, and watchdog dismiss controls can be selected
  by durable accessible role/name queries.
- Existing callbacks still fire in focused tests where practical.
- No forbidden surfaces are touched.
- PR references #53 and clearly states this is a partial remediation slice.
