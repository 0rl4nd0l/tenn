# Docs Impact

## Decision

- docs_impact: <DOCS_NOT_REQUIRED|DOCS_UPDATED|DOCS_FOLLOWUP|DATA_MISSING>
- reason: <short reason>

## Evidence

- docs_checked:
  - <path or none>
- docs_changed:
  - <path or none>
- docs_followup:
  - <issue, task card, report path, or none>

## Freshness Metadata

Use these fields for durable docs, templates, skills, runbooks, and other
control-plane surfaces where stale instructions would mislead future agents.

- last_verified_commit: <sha or DATA_MISSING>
- last_verified_pr: <PR number, none, or DATA_MISSING>
- source_of_truth_files:
  - <path or none>
- stale_if_files:
  - <path or none>
- owner: <role, lane, or owner>
- evidence_grade: <VERIFIED|USER_REPORTED|INFERRED|UNKNOWN|CONFLICT>

## Decision Rules

- Use `DOCS_UPDATED` when affected docs, templates, or skills were updated in
  this change.
- Use `DOCS_FOLLOWUP` when docs should change but the update is intentionally
  deferred to a concrete issue, report, or task card.
- Use `DOCS_NOT_REQUIRED` only when behavior, schema, command usage, workflow,
  validation, operator steps, artifact shape, API, data model, skill trigger,
  and safety boundaries did not change.
- Use `DATA_MISSING` when docs impact cannot be determined from current
  evidence.
