# Merge Parking Registry Surface Safe Extension

## Scope

- Source design: `merge_parking_registry_surface_audit_design_v1_20260525`.
- Lane: Reporting.
- Execution mode: SAFE EXTENSION.
- Target system layer: agent coordination docs only.
- Contract boundary: no branch/worktree mutation, merge, rebase, cherry-pick, runtime/config/source/data-store changes, or automatic parking of existing work.

## Result

Created a committed docs-owned merge parking registry surface:

- `docs/agent_registry/merge_parking/REGISTRY.md`
- `docs/agent_registry/merge_parking/schema.md`
- `docs/agent_registry/merge_parking/parked/README.md`

The initial registry contains zero parked records. That is intentional: the safe extension provides the surface and schema, but does not auto-park existing work without owner approval.

## Safety Notes

- Parking is visibility only; it does not grant merge approval.
- Parked records must set `requires_owner_approval: true` for any merge action.
- Missing evidence must be represented as `DATA_MISSING`.
- The registry must not store production data, secrets, memory rows, financial truth, or runtime state.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/merge_parking_registry_surface_safe_extension_v1_20260525.md`: passed.
- `python3 scripts/agent_job_registry.py list-active`: passed.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/merge_parking_registry_surface_safe_extension_v1_20260525.md`: passed.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/merge_parking_registry_surface_safe_extension_v1_20260525.md`: passed.
- `python3 scripts/agent_job_registry.py release merge_parking_registry_surface_safe_extension_v1_20260525`: passed.
- `python3 -m json.tool reports/agent_jobs/merge_parking_registry_surface_safe_extension_v1_20260525/status.json`: passed.
- `python3 -m json.tool reports/agent_jobs/merge_parking_registry_surface_safe_extension_v1_20260525/validation.json`: passed.
- `git diff --check`: passed.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/merge_parking_registry_surface_safe_extension_v1_20260525.md`: passed.
