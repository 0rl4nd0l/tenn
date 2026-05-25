# Merge Parking Record Schema

Parking records are JSON files under `docs/agent_registry/merge_parking/parked/`.

Use one file per parked job:

```text
docs/agent_registry/merge_parking/parked/<job_id>.json
```

## Required Fields

```json
{
  "job_id": "example_job_v1",
  "issue_or_pr": "DATA_MISSING",
  "lane": "Reporting",
  "owner": "Codex",
  "branch": "safe/example-branch",
  "worktree": "/abs/path/to/worktree",
  "commit_sha": "DATA_MISSING",
  "task_card": "docs/agent_tasks/example_job_v1.md",
  "report_dir": "reports/agent_jobs/example_job_v1",
  "validation_summary": "DATA_MISSING",
  "merge_status": "parked",
  "requires_owner_approval": true,
  "last_verified_at": "2026-05-25T00:00:00Z",
  "notes": "Short operator-facing summary."
}
```

## Field Rules

- `job_id`: must match the task-card job id when one exists.
- `issue_or_pr`: GitHub issue/PR reference, or `DATA_MISSING`.
- `lane`: one of Tenn's task-card lanes.
- `owner`: agent or person responsible for the parked work.
- `branch`: branch containing the parked commit, or `DATA_MISSING`.
- `worktree`: absolute worktree path if still present, or `DATA_MISSING`.
- `commit_sha`: exact commit SHA if committed, or `DATA_MISSING`.
- `task_card`: task-card path, or `DATA_MISSING`.
- `report_dir`: report artifact path, or `DATA_MISSING`.
- `validation_summary`: short validation result, not a merge claim.
- `merge_status`: `parked`, `merged`, `superseded`, or `abandoned`.
- `requires_owner_approval`: must be `true` unless the record is already `merged`, `superseded`, or `abandoned`.
- `last_verified_at`: ISO-8601 timestamp from the verifying agent.
- `notes`: short summary of what the parked work is and why it is parked.

## Non-Goals

This schema does not authorize merging, deleting, pruning, or cleaning anything. It only makes parked work discoverable.
