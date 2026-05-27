# DATA_MISSING

| Item |
| --- |
| GitHub Project field schema/access was not queried; issue bodies provide recommended Project fields but current Project truth is DATA_MISSING. |
| GitHub issue timeline/state_reason was unavailable through gh issue list JSON fields; closure reasons are inferred from labels/comments only. |
| Jam evidence for raw #40/#41 was not opened in this audit; exact duplicate/supersession needs Jam evidence extraction. |
| Exhaustive branch-to-issue mapping for all 248 worktrees was not proven; #115/lock-up branch_matrix is the right bounded follow-up. |
| Open PR CI/log details were not fully inspected; PR alignment uses metadata/merge state, not Actions log root cause except existing issue #105/#66 evidence. |
| Local ahead commits a7da52d2 and 3725591c are not on origin/migration/clean-runtime-baseline-reconstruct-v1; remote publication/merge status remains pending by policy. |

## Branch / Worktree Risk Notes

| Area | DATA_MISSING / Risk |
| --- | --- |
| Current branch publication | Local branch is ahead of origin by 2; no push/merge/PR update was approved in this audit. |
| Project fields | Recommended Project fields exist in issue bodies, but current GitHub Project schema/values were not queried. |
| Issue timeline/state reason | gh issue JSON fields did not expose stateReason or full timeline events. |
| Jam evidence | Raw Jam issues #40/#41 require Jam evidence extraction before duplicate/stale closeout. |
| Worktree coverage | 248 worktrees observed; exhaustive branch-to-issue matrix was not proven here. Run/review #115 branch_matrix. |
| PR CI logs | PR merge state was collected, but Actions logs were not pulled for every open PR. |
