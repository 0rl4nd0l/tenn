## Tenn Issue Contract Normalization

Task: `cockpit_accessible_form_controls_audit_v1_20260526`

Classification: normalized in place as a task-card-ready audit/remediation
candidate.

## Lane

Primary lane: Reporting
Supporting lanes: Cockpit, Evaluation
Mode: audit_first

## GitHub Tracking

Recommended labels applied by #106 normalization: `lane:reporting`, `lane:cockpit`, `mode:audit`, `priority:p2`, `risk:medium`, `state:ready`, `type:usability`, `type:validation-gap`

Milestone: M5 - Cockpit Analyst Workflow

## Source Evidence

The original audit found visible inputs and icon controls without durable
accessible names across `/full-chat`, `/holdings`, `/news`, `/verification`,
`/marketplace`, `/memory`, `/thesis-audit`, `/updater`, `/intel-ops`,
`/history`, and `/verification`.

Representative code pointers from the original report:

- `cockpit-ui/components/cockpit/chat/terminal-input.tsx:164-175`
- `cockpit-ui/components/cockpit/holdings/holdings-screen.tsx:753-836`
- `cockpit-ui/components/cockpit/news/news-screen.tsx:292-330`
- `cockpit-ui/components/cockpit/history/history-screen.tsx:79-86`

Original audit artifact path recorded by the raw issue:
`/tmp/tenn-ui-production-deep-audit.json`.

## Why This Matters

Placeholder-only controls lose context after typing and are weak for keyboard,
screen-reader, browser autofill, and dense production workflows. Icon-only
controls without accessible names are also hard to audit and automate safely.

## Required Task Card

`docs/agent_tasks/cockpit_accessible_form_controls_audit_v1_20260526.md`

## Required Report Path

`reports/agent_jobs/cockpit_accessible_form_controls_audit_v1_20260526/`

## Allowed Files / Surfaces

- Task card and report artifacts.
- Read-only DOM/accessibility audits across affected Cockpit routes.
- Focused Cockpit UI component files only in a later implementation task that
  names exact files.
- Focused accessibility tests or Playwright checks only in a later safe-extension task.

## Forbidden Files / Surfaces

- Backend/runtime/data/memory changes.
- Canonical financial truth mutation.
- Parser routing, extraction prompts, gold labels, model/runtime/GPU/service config changes.
- Broad UI redesign unrelated to accessible names.
- Removing visible labels or relying only on placeholders as the final state.
- Unrelated dirty work.

## Validation

- Run a DOM/accessibility audit that fails on visible form controls without accessible names.
- Verify every input, select, and textarea has `label`, `aria-label`, or `aria-labelledby`.
- Verify every icon-only button has an action-specific accessible name.
- Verify Radix `Switch` and `Checkbox` controls are programmatically associated with visible labels.
- Run focused UI tests for representative routes after any later implementation.

## Hard Stops

- Duplicate tracker found.
- The audit artifact is unavailable and current route evidence cannot be reproduced.
- A proposed fix requires broad UI redesign outside an approved task card.
- Validation cannot distinguish visible labels from programmatic accessible names.

## Definition of Done

- Every affected route is audited or explicitly marked `DATA_MISSING`.
- Any remediation task lists exact files and validation checks.
- Accessible names are proven by DOM/test evidence, not by visual inspection alone.
- No forbidden surfaces are changed.

## DATA_MISSING

- The original `/tmp/tenn-ui-production-deep-audit.json` is not a durable repo artifact.
- Current route-by-route accessible-name inventory at the active HEAD.
- Whether every original code pointer still exists unchanged.

## Follow-Up / Parking / Dependencies

- No exact duplicate found during #106 normalization.
- Adjacent UI/usability issues such as #46 and #91 do not cover this accessible-name contract.
