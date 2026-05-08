# Task Card Classification Matrix

## Scope
Only these five scoped task cards were evaluated:
- `docs/agent_tasks/cockpit_runtime_worktree_visibility_audit_20260507.md`
- `docs/agent_tasks/cockpit_home_news_snapshot_v1_20260508.md`
- `docs/agent_tasks/metric_extraction_current_state_audit_v1.md`
- `docs/agent_tasks/metric_extraction_runtime_contract_reconciliation_v1.md`
- `docs/agent_tasks/reconcile_cockpit_home_news_snapshot_add_path_blocker_20260508.md`

The new meta-audit card is recorded as context (`docs/agent_tasks/remaining_task_cards_classification_audit_20260508.md`) and is excluded from preservation recommendations.

## Matrix

| Artifact | Exists | Git state | Size / mtime | Contract validation | Primary lane | Touch tags | Match report dir | Recent commit evidence | Registry overlap | Classification | Cleanup recommendation |
|---|---|---|---|---|---|---|---|---|---|---|
| cockpit_runtime_worktree_visibility_audit_20260507 | yes | tracked modified (`M`) | 448 bytes / 2026-05-08 19:19:56 | ok | Reporting | Repo Hygiene, Runtime/Router | yes (`reports/agent_jobs/cockpit_runtime_worktree_visibility_audit_20260507`) | no active | HIGH | `revert_later_if_confirmed_accidental_modification` |
| cockpit_home_news_snapshot_v1_20260508 | yes | untracked | 1744 / 2026-05-08 17:34:02 | ok | Reporting | Cockpit UI, News substrate | yes (`reports/agent_jobs/cockpit_home_news_snapshot_v1_20260508`) | no active | HIGH | `preserve_later_in_lane_specific_commit` |
| metric_extraction_current_state_audit_v1 | yes | untracked | 1739 / 2026-05-08 17:28:38 | ok | Evaluation | Metric Extraction | yes (`reports/agent_jobs/metric_extraction_current_state_audit_v1`) | no active | HIGH | `preserve_later_in_lane_specific_commit` |
| metric_extraction_runtime_contract_reconciliation_v1 | yes | untracked | 3164 / 2026-05-08 17:53:00 | ok | Evaluation | Metric Extraction, Runtime/Router | yes (`reports/agent_jobs/metric_extraction_runtime_contract_reconciliation_v1`) | no active | HIGH | `preserve_later_in_lane_specific_commit` |
| reconcile_cockpit_home_news_snapshot_add_path_blocker_20260508 | yes | untracked | 1614 / 2026-05-08 18:57:24 | ok | Evaluation | Cockpit UI, Repo Hygiene | yes (`reports/agent_jobs/reconcile_cockpit_home_news_snapshot_add_path_blocker_20260508`) | no active | MEDIUM | `leave_until_related_job_finishes` |

## Contract/validation notes
- All five scoped cards include valid YAML frontmatter and pass `python3 scripts/agent_job_contract.py validate` with no parser issues.
- `git log --all -- docs/<task_card>` returns commit history for `cockpit_home_news_snapshot_v1_20260508` (`c0549d7`) and no commit history for the other untracked scoped cards in this branch history.
- `git status --short --untracked-files=all` confirms only dirty files above and one additional unscoped `docs/agent_tasks/preserve_baseline_failure_classification_20260508.md`.

## Special check on modified tracked file
`docs/agent_tasks/cockpit_runtime_worktree_visibility_audit_20260507.md` changed from a body+task description to YAML-only metadata. The prior commit version (`b779f0a`) contains a full task statement and boundaries, indicating likely accidental truncation or overwrite.
