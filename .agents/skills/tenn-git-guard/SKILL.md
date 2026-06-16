---
name: tenn-git-guard
description: Native Tenn Git Hygiene backend guard for branch, worktree, dirty-state, PR, and registry preflight. Use inside Tenn issue, review, fix, worker, explain, code-review, and architecture workflows before any mutation or readiness claim.
---

# Tenn Git Guard

`tenn-git-guard` is a quiet backend guard. It is not a user-facing cleanup
command by default.

Use it before `/issue`, `/review-board`, `/fix`, `worker`,
`/explain` for branch or PR topics, `code-reviewer`, and architecture work. Use
the existing `tenn-git-hygiene` skill for deeper cleanup planning, but keep this
wrapper focused on preflight and stop decisions.

## Preflight

Collect current evidence before relying on repo state:

```bash
pwd
git branch --show-current
git rev-parse HEAD
git remote -v
git rev-parse --abbrev-ref --symbolic-full-name @{u}
git merge-base HEAD origin/migration/clean-runtime-baseline-reconstruct-v1
git status --short --untracked-files=all
python3 scripts/agent_job_registry.py list-active --read-only --repo-root .
```

If branch or PR context matters, use read-only GitHub inspection before
suggesting mutation:

```bash
gh pr list --state all --search "<branch-or-topic>" --json number,title,state,headRefName,baseRefName,updatedAt
gh issue list --state all --search "<topic>" --json number,title,state,updatedAt,labels
```

Record `DATA_MISSING` for unavailable commands, missing auth, missing upstream,
or unsafe command surfaces.

## Classify

Classify the worktree and dirty files:

- task-card or report artifact
- hook/config/control-plane file
- product/runtime/data path
- extraction/source/gold-label path
- generated or cache path
- owner-boundary or unknown path
- related PR or issue
- registry active job or `DATA_MISSING`

Block or narrow the workflow when dirty state overlaps the requested mutation
surface and ownership is unclear.

## Allowed Output

Produce short markdown or JSON in the caller's report directory:

- worktree path
- branch
- HEAD
- base and upstream
- dirty file summary
- owner-boundary paths
- related PRs/issues
- registry read-only status
- decision: `pass`, `warning`, `block`, or `data_missing`

## Prohibited Actions

Do not clean, delete, reset, stash, merge, rebase, cherry-pick, push, force-push,
prune, close issues, comment on GitHub, mutate registry state, or remove
worktrees. Cleanup requires a separate explicit owner approval and a task card.
