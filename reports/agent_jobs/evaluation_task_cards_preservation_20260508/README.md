# Evaluation Task Cards Preservation Report

## Executive summary
Preserved the completed remaining-task-cards classification audit task card and report bundle, plus the two high-value Evaluation task cards (`metric_extraction_current_state_audit_v1`, `metric_extraction_runtime_contract_reconciliation_v1`), and this preservation task/report itself.

## Branch / starting HEAD
- Branch: `preserve/dirty-work-20260430T065748Z`
- Starting HEAD: `47d72fcf5a0db132debb5fe490964acfd6be5a78`

## Active registry status
- Active jobs: none
- Registry root: `/mnt/sdb2/home/l4nd0/tenn/.git/tenn-agent-registry`
- Overlap check: blocked by dirty files outside `allowed_files` (`docs/agent_tasks/cockpit_runtime_worktree_visibility_audit_20260507.md`, `docs/agent_tasks/cockpit_home_news_snapshot_v1_20260508.md`, `docs/agent_tasks/preserve_baseline_failure_classification_20260508.md`, `docs/agent_tasks/reconcile_cockpit_home_news_snapshot_add_path_blocker_20260508.md`).

## Files intentionally preserved
- `docs/agent_tasks/evaluation_task_cards_preservation_20260508.md`
- `docs/agent_tasks/remaining_task_cards_classification_audit_20260508.md`
- `docs/agent_tasks/metric_extraction_current_state_audit_v1.md`
- `docs/agent_tasks/metric_extraction_runtime_contract_reconciliation_v1.md`
- `reports/agent_jobs/remaining_task_cards_classification_audit_20260508/README.md`
- `reports/agent_jobs/remaining_task_cards_classification_audit_20260508/status.json`
- `reports/agent_jobs/remaining_task_cards_classification_audit_20260508/task_card_matrix.md`
- `reports/agent_jobs/remaining_task_cards_classification_audit_20260508/lane_separated_preservation_plan.md`
- `reports/agent_jobs/remaining_task_cards_classification_audit_20260508/do_not_touch_yet.md`
- `reports/agent_jobs/evaluation_task_cards_preservation_20260508/README.md`
- `reports/agent_jobs/evaluation_task_cards_preservation_20260508/status.json`

## Files explicitly not staged
- `docs/agent_tasks/cockpit_runtime_worktree_visibility_audit_20260507.md`
- `docs/agent_tasks/cockpit_home_news_snapshot_v1_20260508.md`
- `docs/agent_tasks/preserve_baseline_failure_classification_20260508.md`
- `docs/agent_tasks/reconcile_cockpit_home_news_snapshot_add_path_blocker_20260508.md`

## Whether report files required `git add -f`
Yes. `reports/` paths are ignored in `.git/info/exclude`.

## Staged diff check
Run time: after staging completed and before commit.
- `git diff --cached --name-status`
- `git diff --cached --stat`
(Values captured in the post-stage output.)

## Commit SHA if successful
Pending.

## Remaining dirty files after commit
Pending.

## Cleanup remains blocked / not performed
Blocked by required scope constraints and user hard boundary: cannot stage or clean up dirty files outside `allowed_files`.

## Next recommended lane-specific cleanup
- Evaluation: begin `docs/agent_tasks/remaining_task_cards_classification_audit_20260508.md` follow-up actions once blocking task cards are triaged into separate audit/follow-up cards.
- Reporting: address `cockpit_runtime_worktree_visibility_audit_20260507.md`, `cockpit_home_news_snapshot_v1_20260508.md`, `reconcile_cockpit_home_news_snapshot_add_path_blocker_20260508.md`, and `preserve_baseline_failure_classification_20260508.md` in a separate Reporting/Cockpit-safe context.

## Project Memory save recommendation
Save this preservation outcome in project memory and keep the blocked-file list as an explicit handoff so later cleanup sessions can pick it up under controlled overlap checks.
