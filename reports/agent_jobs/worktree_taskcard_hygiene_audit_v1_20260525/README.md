# Worktree And Task-Card Hygiene Audit

## Scope

- GitHub issue: #64.
- Lane: Reporting, mapped from the issue's repo-hygiene audit intent because the task-card validator does not define a Repo Hygiene lane.
- Execution mode: AUDIT MODE.
- Target system layer: agent coordination, worktree hygiene, and report visibility only.
- Contract boundary: no delete, prune, clean, reset, stash, checkout, restore, move, merge, runtime, config, service, source-code, or data-store changes.

## Findings

1. Current audit worktree: branch `audit/repo-hygiene-safe-audits-v1-20260525`, current HEAD `17896fcbbad5` at evidence time, with only this task card dirty before report creation.
2. Worktree inventory: `git worktree list --porcelain` reported 221 worktrees and 22 entries marked prunable.
3. Prunable classification: `git worktree prune --dry-run --verbose` listed 22 removals, all with `gitdir file points to non-existent location`. No pruning was performed.
4. Branch inventory: 243 local branches and 39 `origin/*` refs were observed. Local branch activity buckets were 56 branches <=7 days, 155 branches 8-30 days, 32 branches 31-90 days, and 0 branches >90 days by committer date.
5. Task-card inventory: 207 tracked `docs/agent_tasks/*.md` files were observed. The audit worktree had one dirty task card, this audit card.
6. The original NVMe baseline worktree at `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` is ahead of origin and currently has four untracked task cards. That state was inspected read-only.
7. The shared preserve worktree at `/mnt/sdb2/home/l4nd0/tenn` is dirty across backend, scripts, cockpit UI, docs, and 14 untracked task cards plus `skills-lock.json`. That state was inspected read-only and not touched.
8. Report artifact visibility risk is confirmed: `.git/info/exclude:31` ignores `reports/`, so report artifacts are not visible to git by default unless force-added or surfaced through another committed registry.
9. Registry overlap risk at claim time was LOW: `check-overlap` passed and active registry state contained only this audit job after claim.

## Classification

- Worktree count: high.
- Prunable worktree category: stale metadata entries with missing gitdir targets.
- Safe cleanup status: blocked on explicit owner-approved cleanup task or freeze. Dry-run evidence is enough to plan cleanup, not enough to execute it in this audit.
- Loose task-card risk: confirmed in non-audit worktrees. The NVMe baseline has four untracked task cards; the preserve worktree has 14 untracked task cards. Ownership and preservation intent are DATA_MISSING in this audit.
- Ignored report risk: confirmed. `reports/` ignored-by-default makes completed work easier to miss without force-added artifacts, issue comments, or a merge parking registry.

## Safe Cleanup Prerequisites

Before any cleanup task:

- Freeze or explicitly scope the target worktree.
- Re-run `git worktree list --porcelain` and `git worktree prune --dry-run --verbose`.
- Confirm no active registry claim owns the candidate paths.
- Require owner approval before pruning stale worktree metadata.
- Do not clean or move untracked task cards until their report directory, branch/worktree, and owner intent are classified.
- Use task-card allowlists for any cleanup artifacts.

## Recommended Child Tasks

1. `stale_worktree_metadata_prune_approval_v1_20260525`: approval-gated pruning of the 22 dry-run stale entries only, after a fresh dry run.
2. `loose_taskcard_preservation_classification_v1_20260525`: read-only classification of the four untracked NVMe baseline cards and 14 preserve-worktree cards.
3. `report_visibility_registry_safe_extension_v1_20260525`: committed registry or merge-parking surface for ignored report directories.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/worktree_taskcard_hygiene_audit_v1_20260525.md`: passed.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/worktree_taskcard_hygiene_audit_v1_20260525.md`: passed.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/worktree_taskcard_hygiene_audit_v1_20260525.md`: passed.
- `python3 scripts/agent_job_registry.py release worktree_taskcard_hygiene_audit_v1_20260525`: passed.
- `python3 -m json.tool reports/agent_jobs/worktree_taskcard_hygiene_audit_v1_20260525/hygiene_inventory.json`: passed.
- `python3 -m json.tool reports/agent_jobs/worktree_taskcard_hygiene_audit_v1_20260525/status.json`: passed.
- `git diff --check`: passed.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/worktree_taskcard_hygiene_audit_v1_20260525.md`: passed.
