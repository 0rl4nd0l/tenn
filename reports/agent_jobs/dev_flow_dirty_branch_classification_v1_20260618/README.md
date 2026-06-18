# Dev Flow Dirty Branch Classification V1

## Objective

Classify the dirty worktree on
`control-plane/dev-flow-agent-task-ledger-v1-20260616` against current canonical
and recent dev-flow PRs, then preserve only genuinely novel work.

## Current State

`DONE_WITH_RISK`

The requested dirty files were classified. One novel guidance section was
preserved in a clean sibling worktree as an additive patch on canonical and
opened as PR #374:
`https://github.com/0rl4nd0l/tenn/pull/374`.

The original dirty checkout was not cleaned, reset, stashed, deleted, or edited.

## Current-Turn Evidence

- Fetched canonical:
  `origin/migration/clean-runtime-baseline-reconstruct-v1` at
  `98e632996aae3bff82627a02b75e64cddd927420`.
- Original dirty checkout:
  `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Physical path verified with `pwd -P` and `realpath`.
- Original branch:
  `control-plane/dev-flow-agent-task-ledger-v1-20260616`.
- Original HEAD:
  `137535b81a5b60d1f94ca630605caadccc4e1b99`.
- Original upstream:
  `origin/control-plane/dev-flow-agent-task-ledger-v1-20260616`.
- Original status:
  three modified skill files and two untracked task cards.
- Registry read-only status:
  `active_jobs: []`.
- Live PR state checked with `gh pr view` for #367, #368, #370, and #373.
- Clean preservation worktree:
  `/home/l4nd0/tenn-validation-environment-autonomy-preserve-v1-20260618`.
- Clean preservation branch:
  `control-plane/validation-environment-autonomy-preserve-v1-20260618`.
- Preservation PR:
  `https://github.com/0rl4nd0l/tenn/pull/374`.

## Files Touched In Clean Worktree

- `.agents/skills/tenn-fix/SKILL.md`
- `.agents/skills/tenn-git-guard/SKILL.md`
- `.agents/skills/tenn-worker/SKILL.md`
- `docs/agent_tasks/validation_environment_autonomy_skill_update_v1_20260617.md`
- `reports/agent_jobs/dev_flow_dirty_branch_classification_v1_20260618/README.md`
- `reports/agent_jobs/dev_flow_dirty_branch_classification_v1_20260618/PR_STATE.md`
- `reports/agent_jobs/dev_flow_dirty_branch_classification_v1_20260618/DIRTY_FILES.md`
- `reports/agent_jobs/dev_flow_dirty_branch_classification_v1_20260618/CLASSIFICATION.md`
- `reports/agent_jobs/dev_flow_dirty_branch_classification_v1_20260618/NOVEL_DIFFS.md`
- `reports/agent_jobs/dev_flow_dirty_branch_classification_v1_20260618/NEXT_ACTION.md`
- `reports/agent_jobs/dev_flow_dirty_branch_classification_v1_20260618/VALIDATION.md`

## Files Intentionally Not Touched

- The original dirty checkout and its modified/untracked files.
- The old branch's two local ahead commits.
- Tenn product/runtime/data/extraction/count-24 files.
- Host-global files.
- OpenCode bridge files from PR #370/#373.

## Decision

The dirty guidance is not already covered by #367, #368, #370, or #373.
However, the raw dirty patch is stale because it would remove PR #368's
docs-impact and model/worker-routing content from the same files. The useful
work is the validation-environment guidance only, so the clean preservation
patch adds that section without deleting current canonical content.

## Remaining Risk

GitHub checks for PR #374 were still pending at the last live check:
`lint-and-test` was queued and `scan` was in progress.

The old branch itself still has two local commits not on canonical:

- `90dda42a735b61f170f008a815bf1c8aafb455d6`:
  `Add weather track feature utility packet`
- `137535b81a5b60d1f94ca630605caadccc4e1b99`:
  `fix: quote git hygiene skill description`

Those committed changes were outside this request's approved dirty-file scope,
so no branch cleanup recommendation should be treated as safe until those commits
receive a separate owner decision.

## Next Recommended Prompt

After the preservation PR is reviewed, decide whether the original dirty branch
should be cleaned, parked, or separately audited for its two unmerged local
commits.
