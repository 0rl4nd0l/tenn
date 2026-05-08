# Repo Hygiene Classification Audit: `repo_hygiene_classification_audit_20260508`

## Executive summary

This was a read-only hygiene classification audit across the main worktree and all known worktrees. No cleanup was executed. Repository state is a large multi-worktree workspace (`62` total), with `3` prunable and `3` detached entries. Main worktree currently has `1` tracked modification and `5` untracked task artifacts. Several task cards referenced by earlier context are missing from disk (recoverable from git history).

## Confirmed facts

- Main branch/head at audit:
  - branch `preserve/dirty-work-20260430T065748Z`
  - HEAD `13fd78de7ccbacc4b04e15b8d8dcfc52e26932cb`
- Main `git status --short --untracked-files=all`:
  - ` M docs/agent_tasks/cockpit_runtime_worktree_visibility_audit_20260507.md`
  - `?? docs/agent_tasks/cockpit_home_news_snapshot_v1_20260508.md`
  - `?? docs/agent_tasks/metric_extraction_current_state_audit_v1.md`
  - `?? docs/agent_tasks/metric_extraction_runtime_contract_reconciliation_v1.md`
  - `?? docs/agent_tasks/reconcile_cockpit_home_news_snapshot_add_path_blocker_20260508.md`
  - `?? docs/agent_tasks/repo_hygiene_classification_audit_20260508.md`
- Total worktrees listed by `git worktree list`: `62`
- Prunable worktrees (`--porcelain`): `3`
- Detached worktrees (`--porcelain`): `3`
- Active registry job exists (`shared_router_canonical_core_rerun_v1`, lane `Evaluation`) and is running in `/mnt/sdb2/home/l4nd0/tenn-shared-router-strict-eval-gate-v1`.
- Task card validation succeeded after frontmatter correction (`python3 scripts/agent_job_contract.py validate ...` => `ok: true`).

## Inferred facts

- Worktree footprint indicates heavy branching by lane family (especially `codex`, `safe`, `integrate`, `audit`).
- Multiple worktrees are still in “not yet merged” states by `merge-base` ancestry checks and contain untracked/doc artifacts that were likely task-driven scratch.
- Two previously mentioned task cards in earlier context (`news_memo_env_gated_fallback_provenance_*`) are absent from the current working tree but recoverable via historical commits.

## DATA_MISSING

- `docs/agent_tasks/news_memo_env_gated_fallback_provenance_integration_v1.md` and `docs/agent_tasks/news_memo_env_gated_fallback_provenance_v1.md` are absent in this workspace.
- Commit/branch linkage for these absent task files is only inferable via `git log --all --name-only` lookups, not through current filesystem presence.

## Main worktree status

- Branch: `preserve/dirty-work-20260430T065748Z`
- Tracked modified: `1` (`docs/agent_tasks/cockpit_runtime_worktree_visibility_audit_20260507.md`)
- Untracked currently visible: `5`
- Newly created/validated task card added: `docs/agent_tasks/repo_hygiene_classification_audit_20260508.md`

## Untracked artifact classification table

| Artifact | Exists | Likely lane | Classification | Recommendation |
|---|---|---|---|---|
| `docs/agent_tasks/cockpit_home_news_snapshot_v1_20260508.md` | yes | Reporting | active task card to preserve | Preserve |
| `docs/agent_tasks/metric_extraction_current_state_audit_v1.md` | yes | Evaluation | report artifact to preserve | Preserve |
| `docs/agent_tasks/metric_extraction_runtime_contract_reconciliation_v1.md` | yes | Evaluation | active audit work | Preserve |
| `docs/agent_tasks/reconcile_cockpit_home_news_snapshot_add_path_blocker_20260508.md` | yes | Evaluation | active blocker reconciliation | Preserve |
| `docs/agent_tasks/repo_hygiene_classification_audit_20260508.md` | yes | Evaluation | current task card | Preserve and keep in place |
| `docs/agent_tasks/news_memo_env_gated_fallback_provenance_integration_v1.md` | no | Query Orchestration | DATA_MISSING (recoverable in git history) | Archive evidence from history or recreate |
| `docs/agent_tasks/news_memo_env_gated_fallback_provenance_v1.md` | no | Query Orchestration | DATA_MISSING (recoverable in git history) | Archive evidence from history or recreate |

## Dirty worktree table (summary)

| Path | Branch | Main changes | Lane | Risk | Recommendation |
|---|---|---|---|---|---|
| `/mnt/sdb2/home/l4nd0/tenn-eval-instrumentation-20260421` | `audit/eval-instrumentation-bounded-20260421` | 8 tracked backend + eval file changes | Evaluation | High | Preserve, review before archive |
| `/mnt/sdb2/home/l4nd0/tenn-cockpit-home-live-wiring-v1` | `safe/cockpit-home-live-wiring-v1` | `cockpit-ui/next-env.d.ts` | Reporting | Medium | Preserve / branch review |
| `/mnt/sdb2/home/l4nd0/tenn-shared-router-strict-eval-gate-v1` | `codex/shared-router-strict-eval-acceptance-gate-v1` | untracked task card | Evaluation | Medium with active overlap | Preserve; active registry overlap |
| `/mnt/sdb2/home/l4nd0/tenn-ab-isolation-20260421` | `audit/ab-isolation-real-gold-cap-timeout` | untracked script | Evaluation | Low-Medium | Preserve if still needed |
| `/mnt/sdb2/home/l4nd0/tenn-agent-mcp-*` worktrees | `audit/*`/`safe/*` | untracked mcp task cards | Query Orchestration | Low-Medium | Preserve as lane artifact |
| `/mnt/sdb2/home/l4nd0/tenn-cockpit-home-bff-audit-v1` | `audit/cockpit-home-backend-bff-contract-v1` | untracked task card | Reporting | Low-Medium | Preserve as reporting artifact |
| `/mnt/sdb2/home/l4nd0/tenn-source-label-998d68e-integrate` | `codex/source-label-998d68e-clean-integration-20260506` | untracked task card | Reporting | Low-Medium | Preserve as reporting artifact |
| Main worktree | `preserve/dirty-work-20260430T065748Z` | modified + 5 untracked task cards | Reporting/Eval | Medium | Preserve and align with lane task registry |

A detailed matrix is stored at `dirty_worktrees.md`.

## Prunable/detached worktree table

See `prunable_detached_worktrees.md` for full table. Short summary:

- Prunable: 3 (`/home/l4nd0/CLAUDEMAESTRO1`, `/home/l4nd0/Maestro1`, `/tmp/tenn-api-billing-notice`)
- Detached: 3 (`/tmp/tenn-baseline-944fd43`, `/tmp/tenn-metric-coverage-provenance`, `/tmp/tenn-api-billing-notice`)

## Active registry jobs table

| Job | Lane | Branch | Worktree | Status |
|---|---|---|---|---|
| `shared_router_canonical_core_rerun_v1` | Evaluation | `codex/shared-router-strict-eval-acceptance-gate-v1` | `/mnt/sdb2/home/l4nd0/tenn-shared-router-strict-eval-gate-v1` | active |

## Cleanup / preservation recommendations

- Preserve first (no cleanup):
  - `/mnt/sdb2/home/l4nd0/tenn-eval-instrumentation-20260421`
  - `/mnt/sdb2/home/l4nd0/tenn-cockpit-home-live-wiring-v1`
  - `/mnt/sdb2/home/l4nd0/tenn-shared-router-strict-eval-gate-v1` (active overlap)
- Archive/delete later (requires user approval):
  - prunable missing-gitdir worktrees
  - detached worktrees with no unique references
- Do not run `prune/delete/archive` actions in this audit run.

## Hard stops

- `/tmp/tenn-api-billing-notice` and two `/home/...` prunable paths are missing gitdir metadata.
- Active registry overlap exists in shared-router worktree.
- Missing on-disk task-card files mean classification of their current intent is limited to history lookup only.

## Project Memory save

Recommended: **YES** (`SAVE_RECOMMENDED`) to retain:
- branch/folder evidence,
- removed artifact names,
- dry-run cleanup plan,
- active registry overlap and branch-family counts.

## Final git status snapshot

```text
 M docs/agent_tasks/cockpit_runtime_worktree_visibility_audit_20260507.md
?? docs/agent_tasks/cockpit_home_news_snapshot_v1_20260508.md
?? docs/agent_tasks/metric_extraction_current_state_audit_v1.md
?? docs/agent_tasks/metric_extraction_runtime_contract_reconciliation_v1.md
?? docs/agent_tasks/reconcile_cockpit_home_news_snapshot_add_path_blocker_20260508.md
?? docs/agent_tasks/repo_hygiene_classification_audit_20260508.md
```

