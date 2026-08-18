# Issue 234 Current-Base Publish Refresh

date: 2026-06-25
worktree: `/home/l4nd0/tenn-issue234-current-base-publish-v1-20260625`
branch: `control-plane/issue234-diff-check-current-base-v1-20260625`
base: `origin/migration/clean-runtime-baseline-reconstruct-v1`
initial publish base head: `b3b3a154590f36e61d297c1ac79fe623526f0b28`
ready/merge refresh base head: `4f45aaa4a6de9d0ae151c27599a1e19621825382`
source packet commit: `35abf15bd04cf437363aae9e392722ac5a69890a`
source packet parent: `107adb03852558d42795b28c3a5ec887e7cd0c64`

## Purpose

Preserve the existing report-only issue #234 classification packet on the
current canonical base so it can be reviewed through a draft PR.

## Scope

Only the issue #234 task card and report bundle are in scope. The historical
parity artifact remains untouched:

`reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/diff-check.json`

## Current-Base Verification

The historical parity artifact hashes are unchanged between the source packet
and current canonical. Git object evidence uses the blob hash:

```text
40a73fb7048d7e6722da79bce236c87048bd03d7
```

Raw file content evidence uses `sha1sum`:

```text
a47422b732ba09f29a082e02eee4707c22d7bf24
```

The current-base classification remains:

`SUPERSEDED_CURRENT_BASE_CLEAN`

## Boundaries

- No product/runtime/data/extraction files changed.
- No historical parity artifact modification.
- No count-24 packet modification.
- No issue closeout in this publish step.
- No branch or worktree deletion.
- No cleanup, restore, stash, reset, rebase, cherry-pick, or force-push.
- One non-force merge from current canonical into the PR branch is permitted
  only for PR #411 current-base refresh after explicit operator `proceed`.

## Ready/Merge Refresh

After PR #411 opened, PR #410 advanced canonical from
`b3b3a154590f36e61d297c1ac79fe623526f0b28` to
`4f45aaa4a6de9d0ae151c27599a1e19621825382`. The base drift touched skill
surface documentation/report files outside the issue #234 packet. The operator
approved proceeding with a current-base refresh and merge-if-safe lane after
being told the prior draft-only task boundary blocked ready/merge.

The refresh lane may mark PR #411 ready and merge it only after:

- task-card validation passes;
- changed paths remain inside this task-card/report bundle;
- code review has no findings;
- `tenn-git-guard` passes on the refreshed clean branch;
- GitHub checks are green on the refreshed head.

Refresh result:

```text
merge_commit: 17c941772da0d9bd0a1a75b0794abc2c1742dc96
merge_base_with_current_canonical: 4f45aaa4a6de9d0ae151c27599a1e19621825382
conflicts: none
```

After the refresh merge, the PR diff against current canonical still consists
only of this issue #234 task card and report bundle.

## Next Action

Run final validation, push the refreshed branch, wait for green GitHub checks,
mark PR #411 ready, and merge only if all gates remain clean.
