# Merge Parking Registry

This registry is a committed visibility surface for completed-but-not-merged agent work.

It records where parked work can be found. It does not grant merge approval, does not replace task-card ownership, and does not mutate branches, worktrees, or reports.

## Current Parked Records

No parked records are registered in this initial safe extension.

Agents must not auto-add existing branches or worktrees here without owner approval.

## Lifecycle

- `parked`: work is complete or intentionally paused and needs later review before merge.
- `merged`: work was merged or cherry-picked by an approved owner action.
- `superseded`: another task or branch replaces this parked work.
- `abandoned`: the owner intentionally leaves the work unmerged.

## Rules

- Every parked record must live under `docs/agent_registry/merge_parking/parked/`.
- Every parked record must follow `schema.md`.
- `requires_owner_approval` must be `true` for any merge action.
- Parking is visibility only; it is not permission to merge.
- Do not use this registry for production data, secrets, memory rows, financial truth, or runtime state.
- If evidence is stale or unavailable, write `DATA_MISSING` in the parked record instead of guessing.

## Initial Status

Created by `merge_parking_registry_surface_safe_extension_v1_20260525` from the #65 audit/design recommendation.
