# Main worktree untracked and modified artifact classification

## Main worktree status

Audit path: `/mnt/sdb2/home/l4nd0/tenn`

- Branch: `preserve/dirty-work-20260430T065748Z`
- HEAD: `13fd78de7ccbacc4b04e15b8d8dcfc52e26932cb` (`13fd78de7ccb`)
- `git status --short --untracked-files=all` shows:
  - ` M docs/agent_tasks/cockpit_runtime_worktree_visibility_audit_20260507.md`
  - `?? docs/agent_tasks/cockpit_home_news_snapshot_v1_20260508.md`
  - `?? docs/agent_tasks/metric_extraction_current_state_audit_v1.md`
  - `?? docs/agent_tasks/metric_extraction_runtime_contract_reconciliation_v1.md`
  - `?? docs/agent_tasks/reconcile_cockpit_home_news_snapshot_add_path_blocker_20260508.md`
  - `?? docs/agent_tasks/repo_hygiene_classification_audit_20260508.md`

## Tracked modification

- `docs/agent_tasks/cockpit_runtime_worktree_visibility_audit_20260507.md` (modification retained from prior work)
  - File metadata in this card declares lane `Reporting` and a report artifact output.

## Untracked artifact classification

| Artifact | Exists now | Purpose | Completed status | Lane | Classification |
|---|---|---|---|---|---|
| `docs/agent_tasks/cockpit_home_news_snapshot_v1_20260508.md` | yes | Cockpit home market-news snapshot follow-up task card | not completed in-place; references live branch | Reporting | active task card to preserve |
| `docs/agent_tasks/metric_extraction_current_state_audit_v1.md` | yes | Evaluation-only metric extraction audit card + report tree |
| `docs/agent_tasks/metric_extraction_runtime_contract_reconciliation_v1.md` | yes | Evaluation/Provenance contract reconciliation card |
| `docs/agent_tasks/reconcile_cockpit_home_news_snapshot_add_path_blocker_20260508.md` | yes | Evaluation card to reconcile a merge/fileing blocker for the same news-snapshot effort | references branch `integrate/cockpit-home-news-snapshot-v1-20260508` and commit `c0549d7` |
| `docs/agent_tasks/repo_hygiene_classification_audit_20260508.md` | yes | This audit job card | just created/validated (`agent_job_contract` ok) | Evaluation | active task card to preserve |

## Missing artifacts expected by prior context

- `docs/agent_tasks/news_memo_env_gated_fallback_provenance_integration_v1.md` — not on disk now. The path appears in historical commits and commit `3dda92a` (`milestone(provenance): preserve news memo integration artifacts`) and is linked to branch `codex/news-memo-env-gated-fallback-provenance-integration-v1`.
- `docs/agent_tasks/news_memo_env_gated_fallback_provenance_v1.md` — not on disk now. The path appears in historical commits `a3f3933`, `ebae613` and branch `codex/news-memo-env-gated-fallback-provenance-v1`.


