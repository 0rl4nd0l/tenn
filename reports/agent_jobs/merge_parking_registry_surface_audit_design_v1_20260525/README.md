# Merge Parking Registry Surface Audit And Design

## Scope

- GitHub issue: #65.
- Lane: Reporting, mapped from the issue's repo-hygiene audit/design intent because the task-card validator does not define a Repo Hygiene lane.
- Execution mode: AUDIT MODE / DESIGN ONLY.
- Target system layer: agent coordination and report visibility only.
- Contract boundary: no merge, rebase, cherry-pick, parking mutation, branch/worktree mutation, backend, frontend, runtime, config, or data-store changes.

## Findings

1. No repo-visible merge parking registry exists at the checked candidate paths:
   - `docs/agent_registry/merge_parking/REGISTRY.md`
   - `docs/agent_registry/merge_parking/parked/`
   - `.tenn/merge_parking`
   - `.tenn/merge-parking`
   - `reports/merge_parking`
   - `reports/merge-parking`
2. Prior ignored report evidence already classified the same expected `docs/agent_registry/merge_parking/` surface as absent: `reports/agent_jobs/post_quantdinger_milestone_dirt_hygiene_audit_v1_20260524/README.md:90-97`.
3. Tracked task-card evidence shows merge parking is part of the desired repo-native orchestration direction, but not yet implemented as a durable repo surface. Evidence: `docs/agent_tasks/repo_native_orchestration_readiness_audit_v1_20260524.md:28-34`.
4. The current `reports/` tree is ignored through `.git/info/exclude`, so parking metadata stored only under `reports/` would remain easy to miss unless force-added by each agent.

## Classification

- Current absence/presence: Confirmed absent for the checked repo-visible candidate paths.
- Existing protocol status: DATA_MISSING as a formal committed protocol. The repo contains task-card and report references to the need for merge parking, but no committed registry implementation or authoritative runbook was found.
- Risk: Completed-but-unmerged work can remain visible only as branch names, worktrees, GitHub issue comments, and ignored report directories. That is enough for manual recovery, but weak for multi-agent coordination.

## Proposed Design

Create a child safe-extension task to add a committed, docs-owned merge parking surface:

- `docs/agent_registry/merge_parking/REGISTRY.md`: human-readable index of parked work.
- `docs/agent_registry/merge_parking/parked/<job_id>.json`: machine-readable per-job record.
- Optional `docs/agent_registry/merge_parking/schema.md`: schema and lifecycle states.

Recommended parked record fields:

- `job_id`
- `issue_or_pr`
- `lane`
- `owner`
- `branch`
- `worktree`
- `commit_sha`
- `task_card`
- `report_dir`
- `validation_summary`
- `merge_status`: `parked`, `superseded`, `merged`, or `abandoned`
- `requires_owner_approval`: always true for merge action
- `last_verified_at`
- `notes`

## Validation And Diff Implications

- A parking implementation task card should list only the new registry files under `docs/agent_registry/merge_parking/`.
- It must not merge, rebase, cherry-pick, delete, move, prune, clean, stash, reset, or edit parked branches/worktrees.
- The merge parking surface should record work visibility only. It must not imply merge approval.

## Recommended Child Task

`merge_parking_registry_surface_safe_extension_v1_20260525`

Create the committed docs registry surface and seed it with a schema plus zero or explicitly approved parked records. Do not park existing work automatically without owner approval.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/merge_parking_registry_surface_audit_design_v1_20260525.md`: passed.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/merge_parking_registry_surface_audit_design_v1_20260525.md`: passed.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/merge_parking_registry_surface_audit_design_v1_20260525.md`: passed.
- `python3 scripts/agent_job_registry.py release merge_parking_registry_surface_audit_design_v1_20260525`: passed.
- `python3 -m json.tool reports/agent_jobs/merge_parking_registry_surface_audit_design_v1_20260525/merge_parking_design.json`: passed.
- `python3 -m json.tool reports/agent_jobs/merge_parking_registry_surface_audit_design_v1_20260525/status.json`: passed.
- `git diff --check`: passed.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/merge_parking_registry_surface_audit_design_v1_20260525.md`: passed.
