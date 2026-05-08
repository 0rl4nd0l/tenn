# Cleanup plan (audit-only, no execution)

## Phase 0 — No-op safety checks

- Freeze audit-only mode; do not run prune/delete/clean/commit.
- Reconfirm active job registry (`python3 scripts/agent_job_registry.py list-active`) prior to any cleanup.
- Confirm no other process is writing to `/tmp` worktree paths.

## Phase 1 — Preserve / commit / report artifacts

- Preserve all untracked task cards with direct lane evidence:
  - `docs/agent_tasks/cockpit_home_news_snapshot_v1_20260508.md`
  - `docs/agent_tasks/reconcile_cockpit_home_news_snapshot_add_path_blocker_20260508.md`
  - `docs/agent_tasks/metric_extraction_current_state_audit_v1.md`
  - `docs/agent_tasks/metric_extraction_runtime_contract_reconciliation_v1.md`
  - `docs/agent_tasks/repo_hygiene_classification_audit_20260508.md`
- Preserve dirty worktree artifacts that carry production-adjacent value before any cleanup:
  - `/mnt/sdb2/home/l4nd0/tenn-eval-instrumentation-20260421`
  - `/mnt/sdb2/home/l4nd0/tenn-cockpit-home-live-wiring-v1`
  - `/mnt/sdb2/home/l4nd0/tenn-shared-router-strict-eval-gate-v1` (active registry overlap)

## Phase 2 — Review dirty source worktrees

- Inspect `/mnt/sdb2/home/l4nd0/tenn-eval-instrumentation-20260421` changes in full (8 tracked files across backend and scripts).
- Decide whether to continue as branch diff, convert to task-card report, or abandon.
- For remaining doc-only dirty worktrees, attach each untracked task card to correct lane/task registry and archive the branch after confirmation.

## Phase 3 — Prune missing worktrees (manual later)

- Candidate commands (do **not** run now):
  - `git worktree prune`
  - manual branch rebasing/retargeting if any prunable path has unique unresolved commits
- Because `/home/l4nd0/CLAUDEMAESTRO1` and `/home/l4nd0/Maestro1` are listed as prunable with missing gitdir, clean-up safety depends on branch ownership checks.

## Phase 4 — Delete / archive stale worktrees and branches

- Archive/delete after manual validation:
  - `/tmp/tenn-api-billing-notice` (prunable+detached)
  - `/tmp/tenn-metric-coverage-provenance` if no branch claim and no unique evidence remains
- Keep `/tmp/tenn-baseline-944fd43` only if needed for evidence references; otherwise delete/ archive.

## Phase 5 — Project memory update

- If the preservation list changes materially, update:
  - `docs/agent_tasks/*` decision ledger
  - `docs/claude/STATE.md` as required by repo conventions

## Risk and approval

- Cleanup safety today: **requires approval** for prune/delete branches.
- Highest-risk operations:
  - Removing prunable entries without branch-content audit
  - Removing `/mnt/sdb2/home/l4nd0/tenn-eval-instrumentation-20260421`
  - Deleting `/mnt/sdb2/home/l4nd0/tenn-shared-router-strict-eval-gate-v1` while active registry task exists

