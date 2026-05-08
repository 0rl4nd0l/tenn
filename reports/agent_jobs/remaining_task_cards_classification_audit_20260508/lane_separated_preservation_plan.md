# Lane-separated preservation plan

## Evaluation lane
1. Preserve later in lane-specific commit:
   - `docs/agent_tasks/metric_extraction_current_state_audit_v1.md`
   - `docs/agent_tasks/metric_extraction_runtime_contract_reconciliation_v1.md`
   - Keep together with existing `reports/agent_jobs/<job_id>/` evidence; these are high-value evaluation artifacts and currently non-overlapping with active registry jobs.
2. Hold pending completion/follow-through:
   - `docs/agent_tasks/reconcile_cockpit_home_news_snapshot_add_path_blocker_20260508.md`
   - Wait until integration-related home-news blocker context is officially closed before archiving.

## Reporting lane
1. Preserve later in lane-specific commit:
   - `docs/agent_tasks/cockpit_home_news_snapshot_v1_20260508.md`
   - Preserve with its report directory, as branch evidence (`integrate/cockpit-home-news-snapshot-v1-20260508`) exists and output is complete.
2. Investigate and resolve tracked-modified file in next non-audit pass:
   - `docs/agent_tasks/cockpit_runtime_worktree_visibility_audit_20260507.md`
   - Treat as `revert_later_if_confirmed_accidental_modification` because current HEAD snapshot is missing the previously present task body.

## Repo Hygiene coordination note
- Do not co-mingle these decisions with source changes.
- No cleanup action (delete/archive/revert/commit) is allowed in this audit-only run.
