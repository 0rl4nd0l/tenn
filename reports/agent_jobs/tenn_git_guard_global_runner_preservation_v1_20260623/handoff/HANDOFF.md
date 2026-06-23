# Handoff: Tenn Git Guard Global Runner Preservation

## Executive Summary

The repo-backed `tenn-git-guard` surface now contains the portable runner and
tests needed for fresh sessions to preflight runtime/product repos without
requiring those repos to contain Tenn control-plane scripts.

Greyhound runtime guard support now passes, but runtime ledger rows are still
`DATA_MISSING`. Promotion remains blocked.

## Session ID / Thread ID / Goal ID

- session_id: DATA_MISSING
- thread_id: DATA_MISSING
- goal_id: DATA_MISSING

## Branch / Worktree / Base

Control-plane worktree:
`/home/l4nd0/tenn-control-plane-task-ledger-status-refresh-v1-20260623`

Observed start:

- branch: `dev-flow/import-runtime-entrypoint-remediation-v1-20260623`
- HEAD: `ac68c574bfc25770d3a58deb0f421bd317ceb6c2`

Observed final:

- branch: `control-plane/tenn-git-guard-global-runner-preservation-v1-20260623`
- HEAD before preservation commit: `6df3b29783dffe625f74dfbb4870667a4c57b750`
- base: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- status: normalized to current canonical before preservation commit

Runtime worktree:
`/mnt/tenn-nvme2/tenn/offloaded-home/l4nd0/greyhound-runtime-master-live-20260621`

- branch: `codex/runtime-master-live-20260621`
- HEAD: `c96363fbcd708bba78ecfb69e4bc4dacb183d867`
- base: `origin/codex/runtime-master-live-20260621`

## Completed Work

- Added task card:
  `docs/agent_tasks/tenn_git_guard_global_runner_preservation_v1_20260623.md`
- Updated repo-backed guard instructions:
  `.agents/skills/tenn-git-guard/SKILL.md`
- Added repo-backed runner and tests:
  `.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py`
  `.agents/skills/tenn-git-guard/tests/test_tenn_git_guard.py`
- Updated route map:
  `docs/dev_flow/SKILLS_SURFACE.md`
- Wrote report-local guard and runtime closeout artifacts.

## Commits

Commit/push authority was later provided by the owner for this preservation
lane. This packet was updated before commit so it no longer describes the older
mixed-worktree stop state.

## PRs

None created or modified.

## Issues

None created, edited, commented, or closed.

## Files Changed

Guard preservation files:

- `.agents/skills/tenn-git-guard/SKILL.md`
- `.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py`
- `.agents/skills/tenn-git-guard/tests/test_tenn_git_guard.py`
- `docs/dev_flow/SKILLS_SURFACE.md`
- `docs/agent_tasks/tenn_git_guard_global_runner_preservation_v1_20260623.md`
- `reports/agent_jobs/tenn_git_guard_global_runner_preservation_v1_20260623/**`

## Tests And Validation

Passed:

- task-card validate
- guard runner `py_compile`
- guard runner `unittest discover`: 5 tests
- repo-backed guard preflight for control-plane worktree
- repo-backed guard preflight for Greyhound runtime checkout
- task-card `check-diff`
- task-card `check-closeout`
- task-card `check-report-artifacts`
- control-plane `git diff --check`
- control-plane `git diff --cached --check`

## Reports / Task Cards Created

- `reports/agent_jobs/tenn_git_guard_global_runner_preservation_v1_20260623/README.md`
- `reports/agent_jobs/tenn_git_guard_global_runner_preservation_v1_20260623/VALIDATION.md`
- `reports/agent_jobs/tenn_git_guard_global_runner_preservation_v1_20260623/GUARD_SMOKE.json`
- `reports/agent_jobs/tenn_git_guard_global_runner_preservation_v1_20260623/RUNTIME_GUARD_SMOKE.json`
- `reports/agent_jobs/tenn_git_guard_global_runner_preservation_v1_20260623/RUNTIME_DIRTY_CLASSIFICATION.md`
- `reports/agent_jobs/tenn_git_guard_global_runner_preservation_v1_20260623/handoff/LEDGER_ENTRY.json`
- `reports/agent_jobs/tenn_git_guard_global_runner_preservation_v1_20260623/handoff/NEXT_GOAL.md`

## Git Status And Dirt

Control-plane dirt was reduced to this preservation lane before commit.
The `.agents/skills/tenn-git-guard/scripts/`,
`.agents/skills/tenn-git-guard/tests/`, and `reports/` paths are ignored and
were staged explicitly with `git add -f` for preservation.

Greyhound runtime dirt is classified in `RUNTIME_DIRTY_CLASSIFICATION.md`.

## Ledger Status

Control-plane ledger: PASS in `GUARD_SMOKE.json`.

Greyhound runtime ledger: `DATA_MISSING` for `ledger:committed` and
`ledger:live` in `RUNTIME_GUARD_SMOKE.json`.

No live ledger append was performed. Report-local entry:
`handoff/LEDGER_ENTRY.json`.

## Failed Attempts / Mistakes

- Initial task-card lane value `Repo Hygiene` failed validation; corrected to
  supported lane `Reporting`.
- Initial `python3 -m unittest .agents/.../test_tenn_git_guard.py` command
  failed because `unittest` interpreted the leading `.agents` path as an empty
  module name; corrected to `python3 -m unittest discover -s ...`.
- The control-plane worktree branch changed while this run was active. Treat
  the resulting cockpit dirt as owner-boundary.

## Open Risks

- Greyhound runtime ledger rows remain missing.
- Greyhound runtime has dirty rows and needs owner-approved commit grouping.

## Owner Decisions Needed

- Decide how to split Greyhound runtime dirt into coherent commit groups.

## Relevant Artifact Map

- Control guard smoke: `GUARD_SMOKE.json`
- Runtime guard smoke: `RUNTIME_GUARD_SMOKE.json`
- Runtime dirt: `RUNTIME_DIRTY_CLASSIFICATION.md`
- Validation: `VALIDATION.md`
- Next prompt: `handoff/NEXT_GOAL.md`

## What The Next Session Should Do First

Read this handoff, run the repo-backed guard, inspect current branch/status, and
avoid mutating runtime/product repos without a fresh owner-approved lane.

## What Not To Touch

Do not clean, reset, stash, rebase, merge, mutate GitHub beyond this approved
preservation push, mutate registry, or absorb runtime dirt without explicit
owner approval.

Do not mutate DB, runtime services, training, promotion, EV, betting, snapshots,
or identity/source/official-result/pre-jump gates.

## Next Milestones

1. Re-run `tenn-git-guard` in the control-plane worktree.
2. If continuing from the pushed preservation branch, verify GitHub state before
   merge or cleanup.
3. For Greyhound runtime, split dirty rows into coherent commit groups.
4. Keep promotion blocked until 100+ safe eligible races and all gates pass.

## Short Next `/goal`

Work in `/home/l4nd0/tenn-control-plane-task-ledger-status-refresh-v1-20260623`.
Read `reports/agent_jobs/tenn_git_guard_global_runner_preservation_v1_20260623/handoff/HANDOFF.md`
first. Run repo-backed `tenn-git-guard`. Verify preservation branch state and
keep Greyhound promotion blocked.

## Do-Not-Touch Boundaries

No DB mutation, runtime mutation, training, promotion, EV, betting, snapshot
rewrite, registry mutation, branch cleanup, owner-boundary dirt cleanup, or
gate weakening.

## Evidence Grades

- Guard runner preservation: B, implemented and locally validated before commit.
- Runtime guard support: B, guard smoke passes but ledger is missing.
- Runtime promotion readiness: F, still blocked by explicit gate requirements.
