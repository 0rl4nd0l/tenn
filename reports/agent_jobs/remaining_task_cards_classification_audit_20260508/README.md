# Remaining Task-Card Artifacts Classification Audit

## Executive summary
Repository hygiene audit scoped to five lingering task-card artifacts produced a mixed state: one previously tracked task card (`cockpit_runtime_worktree_visibility_audit_20260507.md`) appears accidentally truncated in-working tree, while four additional untracked task cards are complete artifact sets with matching report directories and active registry clean. No source code was touched.

No cleanup was performed (no commit, delete, revert, stage, or reset).

## Branch / HEAD
- Repository: `/mnt/sdb2/home/l4nd0/tenn`
- Branch: `preserve/dirty-work-20260430T065748Z`
- HEAD: `47d72fcf5a0d` (`47d72fcf5a0db132debb5fe490964acfd6be5a78`)

## Active registry status
- `python3 scripts/agent_job_registry.py list-active`: no active jobs
- Shared registry: `/mnt/sdb2/home/l4nd0/tenn/.git/tenn-agent-registry`
- No stale job files found by searching registry for the five scoped job_ids

## Current dirty status
- ` M docs/agent_tasks/cockpit_runtime_worktree_visibility_audit_20260507.md`
- `?? docs/agent_tasks/cockpit_home_news_snapshot_v1_20260508.md`
- `?? docs/agent_tasks/metric_extraction_current_state_audit_v1.md`
- `?? docs/agent_tasks/metric_extraction_runtime_contract_reconciliation_v1.md`
- `?? docs/agent_tasks/reconcile_cockpit_home_news_snapshot_add_path_blocker_20260508.md`
- `?? docs/agent_tasks/remaining_task_cards_classification_audit_20260508.md`

## Classification table

| Artifact | Existence/state | Contract | Job/metadata | Matching report dir | Branch/commit evidence | Primary lane | Tags | Preservation value | Recommendation | Why not now |
|---|---|---|---|---|---|---|---|---|---|
| `docs/agent_tasks/cockpit_runtime_worktree_visibility_audit_20260507.md` | exists, tracked, modified (`M`) | YAML valid | job_id `cockpit_runtime_worktree_visibility_audit_20260507`, lane `Reporting`, owner `Codex`, mutation `audit_only`, output_dir `reports/agent_jobs/cockpit_runtime_worktree_visibility_audit_20260507`, production access `false` | exists, ignored in git (`.git/info/exclude`), has `README.md`, `status.json`, `runtime_processes.txt`, `worktree_matrix.txt` | last matching commit: `b779f0a chore(agent-tasks): record 2026-05-07 session task cards`; no branch/worktree exact slug match | Reporting | Runtime/Router, Repo Hygiene | HIGH | `revert_later_if_confirmed_accidental_modification` | Current diff removed all task body content (owner flip + truncation), so reverting should be validated before any cleanup action. |
| `docs/agent_tasks/cockpit_home_news_snapshot_v1_20260508.md` | exists, untracked (`??`) | YAML valid | job_id `cockpit_home_news_snapshot_v1_20260508`, lane `Reporting`, owner `Codex`, mutation `safe_extension`, output_dir `reports/agent_jobs/cockpit_home_news_snapshot_v1_20260508`, production access `false` | exists, ignored in git, report has `README.md` + `diff-check.json` | matching commit: `c0549d7 milestone(reporting): wire home market update signals` (from `integrate/cockpit-home-news-snapshot-v1-20260508`); branch/worktree names with this context exist (hyphenated branch names) | Reporting | Cockpit UI, News substrate, Repo Hygiene | HIGH | `preserve_later_in_lane_specific_commit` | Audit-only request and mixed dirty state across files requires keeping evidence intact for the owning lane handoff. |
| `docs/agent_tasks/metric_extraction_current_state_audit_v1.md` | exists, untracked (`??`) | YAML valid | job_id `metric_extraction_current_state_audit_v1`, lane `Evaluation`, owner `Codex`, mutation `audit_only`, output_dir `reports/agent_jobs/metric_extraction_current_state_audit_v1`, production access `false` | exists, ignored in git, extensive evaluation artifacts present | no branch/worktree exact slug match; no recent history for file path | Evaluation | Metric Extraction | HIGH | `preserve_later_in_lane_specific_commit` | No active registry overlap, but artifact should be retained for evaluation continuity before cleanup decisions. |
| `docs/agent_tasks/metric_extraction_runtime_contract_reconciliation_v1.md` | exists, untracked (`??`) | YAML valid | job_id `metric_extraction_runtime_contract_reconciliation_v1`, lane `Evaluation`, owner `Codex`, mutation `audit_only`, output_dir `reports/agent_jobs/metric_extraction_runtime_contract_reconciliation_v1`, production access `false` | exists, ignored in git, `README.md` + `diff-check.json` present | no branch/worktree exact slug match; no recent history for file path | Evaluation | Metric Extraction, Runtime/Router | HIGH | `preserve_later_in_lane_specific_commit` | No claim/active job and no commit history in this branch; safe to defer cleanup until Evaluation lane review. |
| `docs/agent_tasks/reconcile_cockpit_home_news_snapshot_add_path_blocker_20260508.md` | exists, untracked (`??`) | YAML valid | job_id `reconcile_cockpit_home_news_snapshot_add_path_blocker_20260508`, lane `Evaluation`, owner `Codex`, mutation `safe_extension`, output_dir `reports/agent_jobs/reconcile_cockpit_home_news_snapshot_add_path_blocker_20260508`, production access `false` | exists, ignored in git, has `README.md` and `diff-check.json` | no branch/worktree exact slug match; explicit integration context points to `integrate/cockpit-home-news-snapshot-v1-20260508` and `codex/cockpit-home-news-snapshot-v1-20260508` | Evaluation | Cockpit UI, News substrate, Repo Hygiene | MEDIUM | `leave_until_related_job_finishes` | Depends on home-news snapshot integration and blocker resolution context; should remain available until that path is closed. |

## Highest-risk file
- `docs/agent_tasks/cockpit_runtime_worktree_visibility_audit_20260507.md` (tracked + modified; body is fully removed compared to committed version, likely unintended truncation).

## Files recommended to preserve later
- `docs/agent_tasks/cockpit_home_news_snapshot_v1_20260508.md`
- `docs/agent_tasks/metric_extraction_current_state_audit_v1.md`
- `docs/agent_tasks/metric_extraction_runtime_contract_reconciliation_v1.md`

## Files recommended to archive/delete later
- None identified yet. `reconcile_cockpit_home_news_snapshot_add_path_blocker_20260508.md` is better held pending related job completion.

## Files that require user approval
- None identified in this audit.

## Files that should not be touched until another job finishes
- `docs/agent_tasks/reconcile_cockpit_home_news_snapshot_add_path_blocker_20260508.md`

## Project Memory save recommendation
- `SAVE_RECOMMENDED` (high-signal audit outcome with five-file classification matrix and evidence anchors).

## Final git status
```text
 M docs/agent_tasks/cockpit_runtime_worktree_visibility_audit_20260507.md
?? docs/agent_tasks/cockpit_home_news_snapshot_v1_20260508.md
?? docs/agent_tasks/metric_extraction_current_state_audit_v1.md
?? docs/agent_tasks/metric_extraction_runtime_contract_reconciliation_v1.md
?? docs/agent_tasks/preserve_baseline_failure_classification_20260508.md
?? docs/agent_tasks/reconcile_cockpit_home_news_snapshot_add_path_blocker_20260508.md
?? docs/agent_tasks/remaining_task_cards_classification_audit_20260508.md
