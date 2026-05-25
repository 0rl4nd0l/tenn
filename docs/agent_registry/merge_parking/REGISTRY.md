---
schema_version: merge_parking_registry_v1
registry_id: merge_parking_registry
status: active
updated_at: "2026-05-25T04:56:00Z"
active_parking_count: 0
recently_resolved_count: 0
notes:
  - Placeholder registry created by merge parking safe-extension work.
  - This index is human-readable documentation, not merge automation.
  - Parking is visibility only and never merge approval.
---

# Merge Parking Registry

This registry is a committed visibility surface for completed-but-not-merged
agent work. It records where parked work can be found. It does not grant merge
approval, replace task-card ownership, or mutate branches, worktrees, reports,
or Git refs.

## Active Parked Items

| Parking ID | Status | Job ID | Source Branch | Current Head | Report Dir | Blocked By | Review Required |
|------------|--------|--------|---------------|--------------|------------|------------|-----------------|
| _none_ | _none_ | _none_ | _none_ | _none_ | _none_ | _none_ | _none_ |

## Recently Resolved

| Parking ID | Final Status | Job ID | Source Branch | Resolution Commit | Notes |
|------------|--------------|--------|---------------|-------------------|-------|
| _none_ | _none_ | _none_ | _none_ | _none_ | _none_ |

## Lifecycle

- `PARKED_READY_FOR_REVIEW`: work is complete enough for a separate review task.
- `PARKED_BLOCKED_BY_DEPENDENCY`: work is complete or paused, but a named dependency blocks review.
- `PARKED_NEEDS_REBASE`: source branch exists but must be rebased before review.
- `PARKED_NEEDS_VALIDATION`: source branch exists but validation is stale or incomplete.
- `PARKED_NEEDS_HUMAN_DECISION`: owner/operator decision is required before the next action.
- `PARKED_SUPERSEDED`: another task or branch replaces this parked work.
- `MERGED`: work was merged or cherry-picked by an approved owner action.
- `REJECTED`: work was reviewed and intentionally not accepted.
- `ABANDONED`: the owner intentionally leaves the work unmerged.

## Operator Notes

- Add new entries by copying `_entry_template.md` to a task-specific file in
  this directory, or by adding a JSON entry matching
  `merge_parking_entry_schema_v1.json`.
- Update this index manually after review or resolution.
- Keep `active_parking_count` and `recently_resolved_count` in the frontmatter
  aligned with the tables in this file.
- Keep detailed parking fields in entry files; this index is for scanning.
- Do not infer that a listed branch is approved to merge.
- Do not use this registry to mutate Git refs, run merges, or bypass a later
  task-card-controlled integration.
- If evidence is stale or unavailable, write `DATA_MISSING` in the parked entry
  instead of guessing.

## Compatibility Notes

The earlier registry surface also introduced `schema.md` and `parked/README.md`
as lightweight operator documentation. Those files remain valid human-readable
context. The machine-checkable entry and registry schemas in this directory are
the validation surface for this slice.
