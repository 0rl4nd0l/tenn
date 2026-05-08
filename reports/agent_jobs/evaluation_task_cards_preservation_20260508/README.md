# Evaluation Task Cards Preservation Report

## Executive summary
Preserved exactly the requested Evaluation-preservation artifacts: the classification-audit task card, its full report bundle, both requested high-value Evaluation task cards, and the new preservation task/report.

## Branch / starting HEAD
- Branch: `preserve/dirty-work-20260430T065748Z`
- Starting HEAD: `47d72fcf5a0db132debb5fe490964acfd6be5a78`
- Final HEAD: `d2ab35c53b8cf4024f98289f8063621853f7e6ab`

## Active registry status
- Active jobs at invocation: none
- Registry root: `/mnt/sdb2/home/l4nd0/tenn/.git/tenn-agent-registry`
- `check-overlap` was not claimable due pre-existing dirty, out-of-scope task cards.

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
- `docs/agent_tasks/cockpit_runtime_worktree_visibility_audit_20260507.md` (pre-existing modified file)
- `docs/agent_tasks/cockpit_home_news_snapshot_v1_20260508.md`
- `docs/agent_tasks/preserve_baseline_failure_classification_20260508.md`
- `docs/agent_tasks/reconcile_cockpit_home_news_snapshot_add_path_blocker_20260508.md`

## Whether report files required `git add -f`
Yes. Report paths are ignored and were added with `git add -f`.

## Staged diff check
- `git diff --cached --name-status`
  - 12 files staged, all under explicit allowed paths.
- `git diff --cached --stat`
  - `12 files changed, 801 insertions(+)`
- `git status --short --untracked-files=all` before commit showed pre-existing dirty/untracked items outside scope.

## Commit SHA if successful
- `d2ab35c53b8cf4024f98289f8063621853f7e6ab`

## Remaining dirty files after commit
- `M docs/agent_tasks/cockpit_runtime_worktree_visibility_audit_20260507.md`
- `?? docs/agent_tasks/cockpit_home_news_snapshot_v1_20260508.md`
- `?? docs/agent_tasks/preserve_baseline_failure_classification_20260508.md`
- `?? docs/agent_tasks/reconcile_cockpit_home_news_snapshot_add_path_blocker_20260508.md`

## Cleanup remains blocked / not performed
Blocked by scope: dirty, out-of-band task cards are explicitly excluded from this preservation pass and were not modified/staged.

## Next recommended lane-specific cleanup
- Evaluation: continue with follow-up from the preserved classification audit and high-value task cards.
- Reporting: address the four explicitly excluded cards in a separate Reporting/Cockpit cleanup lane once scoped.

## Project Memory save recommendation
Save this preservation result and the explicit exclusion list in project memory so the next session can claim the same task-card safely after exclusions are resolved.
