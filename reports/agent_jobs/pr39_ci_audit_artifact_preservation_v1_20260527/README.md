# PR #39 CI Audit Artifact Preservation

## Summary

The completed issue #105 audit bundle and the follow-up preservation-review
bundle were preserved as repo-visible task-card/report artifacts. No PR39
failure-cluster fix was implemented, no product/runtime/test/dependency/workflow
file was edited, and GitHub was inspected read-only only.

The preservation action is `COMMITTED_ALLOWED_ARTIFACTS`: the allowed task cards
and ignored report artifacts are safe to stage with explicit `git add -f`
because this task card permits those exact report paths and task-card
`check-diff` passes for the allowed file set.

## Checkout

| Item | Result |
| --- | --- |
| Worktree path | `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` |
| Worktree realpath | `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` |
| Branch | `migration/clean-runtime-baseline-reconstruct-v1` |
| HEAD at preflight | `c275e3c857cadd8c88491b38c13a3af6debe2539` |
| Initial dirty state | two prior PR39 task cards untracked; two prior report dirs ignored |
| Final intended dirty state | clean after the scoped preservation commit |

## Artifact Inventory

Preserved groups:

- `docs/agent_tasks/pr39_lint_and_test_failure_cluster_split_v1_20260526.md`
- `reports/agent_jobs/pr39_lint_and_test_failure_cluster_split_v1_20260526/`
- `docs/agent_tasks/pr39_ci_split_audit_preservation_review_v1_20260527.md`
- `reports/agent_jobs/pr39_ci_split_audit_preservation_review_v1_20260527/`
- `docs/agent_tasks/pr39_ci_audit_artifact_preservation_v1_20260527.md`
- `reports/agent_jobs/pr39_ci_audit_artifact_preservation_v1_20260527/`

Required prior audit artifacts are present and parseable where applicable:
`README.md`, `status.json`, `failure_clusters.json`,
`child_task_proposals.md`, `pr39_merge_readiness.md`, and `diff-check.json`.

Required preservation-review artifacts are present and parseable where
applicable: `README.md`, `status.json`, `dirty_work_matrix.json`,
`child_task_priority.md`, `preservation_recommendation.md`, and
`diff-check.json`.

## Git Visibility

The two task cards were untracked before preservation. The report directories
were ignored by `/mnt/sdb2/home/l4nd0/tenn/.git/info/exclude` rule
`reports/`, so committing them requires explicit `git add -f`. This task card
allows `git add -f` only for the listed PR39 audit, preservation-review, and
current preservation report artifacts.

No unrelated dirty files were cleaned, stashed, reset, deleted, restored,
overwritten, moved, staged, or committed.

## GitHub State

Read-only `gh` inspection confirmed:

- Issue #105 is open: `[CI] Split PR #39 lint-and-test failure clusters after closed CI audit`.
- PR #39 is open, draft, unmerged, and `UNSTABLE`.
- PR #39 head remains `8635833b7d7359ed55daf0495eb49c5457bab91d`.
- CI run `26439822448` / check `lint-and-test` failed.
- Sloppy Scan run `26439822445` / check `scan` passed.

Issue #105 should stay open. PR #39 should stay draft and remains
`NOT_MERGE_READY / PARKING_RECOMMENDED`.

## Validation

- New preservation task-card validate: passed.
- Prior #105 task-card validate: passed.
- Preservation-review task-card validate: passed.
- Registry `list-active --read-only`: passed; no active jobs.
- Registry `check-overlap`: passed.
- Registry claim: passed.
- Registry release: passed.
- Existing required JSON artifacts: parse passed.
- Generated JSON artifacts: parse target for closeout validation.
- `git diff --check`: required before commit.
- Task-card `check-diff`: passed before staging; rerun required after staging.

## Parking Decision

No merge-parking registry entries were written. The path
`docs/agent_registry/merge_parking/` is absent in this checkout, this task card
does not allow creating it, and a clean artifact-only preservation commit is the
available safer path. Parking remains a recommendation only, not merge approval.

## Next Safe Task

Start with C01:

`[CI] Reconcile backend sqlite3/uuid4/vector invariant failures for PR #39`

Important nuance: reconcile the broad sqlite invariant against documented
SQLite-backed qualitative memory and operational stores before removing or
relaxing anything. Do not mutate production DB/Qdrant/news/memory, canonical
financial truth, parser routing, extraction prompts, gold labels, or
runtime/model/GPU/service config.

## Save Recommendation

Project Memory save is **RECOMMENDED** after review. This preservation commit
makes the #105 audit and preservation-review evidence durable and should guide
the follow-up PR39 child-task queue.
