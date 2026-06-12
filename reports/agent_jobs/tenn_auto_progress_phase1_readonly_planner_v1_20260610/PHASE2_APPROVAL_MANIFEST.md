# Phase 2 Approval Manifest

Default state: no Phase 2 execution approved.

## Recommended Approval Group

Group A: issue #281 issue-to-task-card dry run.

Allowed if approved:

- refresh read-only evidence for #291 and #281
- create a report-local Phase 2 bundle
- draft one real task-card candidate for #281 as report text
- classify expected allowed files, hard stops, and validation
- stop before creating the real task-card file or editing backend/scripts/config

Forbidden:

- executing #281
- touching `financial-engine_v2/**`, `scripts/**`, dependency files, CI, or
  product/runtime/data/extraction surfaces
- installing dependencies
- starting services
- running broad tests or product/runtime/extraction validation
- committing, pushing, or mutating GitHub

Verifier gate:

- issue #281 remains open and `state:ready`
- registry read-only check has no collision
- current dirty state does not overlap the draft output path
- task-card packet has exact allowed files and hard stops

## Alternate Approval Groups

Group B: issue #234 report-only classification packet. This is safer than #281
for product boundaries, but less directly aligned with the #291 example path.

Group C: issue #139 data-missing architecture-rule decision packet. This should
wait for an owner decision on restore vs retire.

## Approval Needed

To continue, approve one group explicitly. Recommended:

```text
Approve Phase 2 Group A only: run an issue-to-task-card dry run for issue #281
under REPORT_AUTONOMY and ISSUE_291_READONLY_PLANNER. Produce report artifacts
only and stop before execution, commits, GitHub writes, product/runtime/data
mutation, service starts, dependency installs, or broad validation.
```
