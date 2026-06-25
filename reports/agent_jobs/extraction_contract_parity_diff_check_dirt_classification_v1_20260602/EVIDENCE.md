# Evidence

## Current Base

- Worktree:
  `/home/l4nd0/tenn-auto-progress-issue234-phase3-dry-run-review-20260615`
- HEAD: `107adb03852558d42795b28c3a5ec887e7cd0c64`
- `origin/migration/clean-runtime-baseline-reconstruct-v1`:
  `107adb03852558d42795b28c3a5ec887e7cd0c64`
- Local branch for commit:
  `control-plane/issue234-diff-check-dirt-classification-v1-20260615`
- Worktree status before report writes: clean detached HEAD at `cdce58fd`;
  before commit closeout, the packet was carried forward to current origin base
  `107adb03852558d42795b28c3a5ec887e7cd0c64` without merge, rebase, or
  cherry-pick.

## PR #344 And Planner

- PR #344 is merged.
- Merged V2 planner files exist on current base, including
  `scripts/auto_progress.py`.
- Merged V2 bundle contains
  `reports/agent_jobs/tenn_auto_progress_issue291_readonly_planner_v2_20260612/CANDIDATE_RANKING.md`
  with #234 ranked first.
- The merged dry-run packet states no #234 execution had occurred and recommends
  creating the real report-only #234 task card before execution.

## Registry

`python3 scripts/agent_job_registry.py list-active --read-only` returned:

- `ok: true`
- `read_only: true`
- `lock_acquired: false`
- `active_jobs: []`

No active registry claim owns the #234 report bundle or the historical #98
parity artifact in this current-base worktree.

## Historical Artifact Current State

Target artifact:

`reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/diff-check.json`

Current-base evidence:

- File exists.
- Git index blob: `40a73fb7048d7e6722da79bce236c87048bd03d7`
- `git hash-object` of working-tree file:
  `40a73fb7048d7e6722da79bce236c87048bd03d7`
- Raw file `sha1sum`: `a47422b732ba09f29a082e02eee4707c22d7bf24`
- `git status --short --untracked-files=all -- <target>` prints no dirty
  status.
- `git log -- <target>` shows the tracked file introduced by
  `82e62c3f milestone(evaluation): integrate extraction eval foundation`.
- The JSON still lists the original #98 changed files, including the task card,
  scorecard service/test files, and report artifacts.

## Shared Checkout Boundary Check

The shared checkout still has the count-24 approval packet as untracked:

`docs/agent_tasks/extraction_count24_approval_packet_current_canonical_v1_20260609.md`

The historical #98 parity artifact is not dirty in the shared checkout from the
safe targeted status check.

## Merge Parking

`docs/agent_registry/merge_parking/REGISTRY.md` does not list issue #234 or the
historical `extraction_contract_parity_guard_v1_20260526/diff-check.json`
artifact as a parked merge item.
