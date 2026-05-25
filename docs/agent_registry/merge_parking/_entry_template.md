---
schema_version: merge_parking_entry_v1
parking_id: example_parking_v1
status: PARKED_READY_FOR_REVIEW
job_id: example_job_v1
lane: Reporting
mode: safe_extension
source_branch: safe/example-job-v1
source_worktree: /home/l4nd0/tenn-example-job-v1
base_head: "0000000000000000000000000000000000000000"
current_head: "1111111111111111111111111111111111111111"
task_card: docs/agent_tasks/example_job_v1.md
report_dir: reports/agent_jobs/example_job_v1
output_dir: reports/agent_jobs/example_job_v1
changed_files:
  - docs/example.md
validation_commands:
  - python3 scripts/agent_job_contract.py validate docs/agent_tasks/example_job_v1.md
  - python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/example_job_v1.md
validation_result: passed
blocked_by: []
ready_for_merge: true
review_required:
  human: true
  gpt: true
  notes:
    - Parking is not merge approval; review is still required.
do_not_merge_before: Review task card, report, diff, validation, branch/head, and registry state.
data_missing: []
next_agent_should:
  - Re-run focused validation if the target base moved.
  - Open a separate integration task card before merge, cherry-pick, or rebase.
next_agent_must_not:
  - Treat parking as approval to merge.
  - Mutate Git refs from the parking entry.
  - Auto-merge, auto-cherry-pick, auto-rebase, reset, stash, or delete branches.
---

# Merge Parking Entry: Example

## Summary

Describe the completed work and why it is parked.

## Review Notes

Record exact review prerequisites, stale validation concerns, dependency
blockers, and any reason the branch should not be merged yet.

## Resolution Notes

When this item is resolved, update `status` and add the reviewed resolution
details here. Do not rewrite history or delete evidence.
