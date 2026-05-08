# Do-not-touch list (audit-only)

Do not modify during this phase:
- `docs/agent_tasks/preserve_baseline_failure_classification_20260508.md` (not in scope for this run)
- `cockpit_runtime` tracked file content until explicit revert decision:
  - `docs/agent_tasks/cockpit_runtime_worktree_visibility_audit_20260507.md`
- Home-news blocker reconciliation dependency chain:
  - `docs/agent_tasks/reconcile_cockpit_home_news_snapshot_add_path_blocker_20260508.md`
- All report trees under:
  - `reports/agent_jobs/*/` for the five scoped job_ids listed in this audit

Reason:
- No active registry job, no stage/commit, and explicit instruction `mutation_mode: audit_only` for the current job; all cleanup must be deferred to a later explicit cleanup job.
