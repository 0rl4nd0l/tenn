---
name: function-quality
description: Perform a deep read-only feature analysis across code, tests, config, and docs, then return structured findings compatible with code-fixer. Use for named feature audits or completeness reviews.
---

# Function Quality

Use this skill when the user names a feature or subsystem and wants a deep quality assessment.

## Inputs

- Feature name
- Optional scope hint such as `backend only` or `scripts/news_pipeline`

## Workflow

### Phase 1: Extract

- Locate code, tests, config, and docs that implement the feature.
- Identify entry points, data flow, dependencies, and coverage.
- Record all files read.

### Phase 2: Analyze

Check for:

- correctness problems
- missing validation or error handling
- test gaps
- docs/code mismatches
- inefficiencies
- robustness issues
- divergence from project patterns or `.cursor/rules/`

Classify each finding as `critical`, `warning`, or `suggestion`.

## Output

Build structured findings with:

- `status`
- `work_log`
- `result.feature`
- `result.summary`
- `result.critical`
- `result.warnings`
- `result.suggestions`
- `result.implementation_notes`

`files_modified` must stay empty.

Default user-facing output should be a normal prose review with findings first. Only emit raw JSON if the user explicitly asks for JSON.

## Constraints

- Read-only. Do not edit files.
- Every finding must be concrete enough to pass directly to `code-fixer`.
