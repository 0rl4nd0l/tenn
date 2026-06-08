# Issue Tracker

Tenn uses GitHub Issues for backlog coordination and PRDs. Task cards and
reports remain separate execution evidence:

- GitHub issues own backlog state, labels, milestones, and coordination.
- Task cards under `docs/agent_tasks/` are execution contracts for scoped work.
- Reports under `reports/agent_jobs/` are evidence, validation, and closeout.
- Merge parking state lives under `docs/agent_registry/merge_parking/`.

Generic skills that say "publish to the issue tracker" should create or update
a GitHub issue only when the user explicitly approves GitHub mutation for the
current task. Otherwise, produce a local draft or report artifact.

## Read-Only Commands

Use these first:

```bash
gh issue view <number> --json number,title,state,labels,milestone,body,comments,url
gh issue list --state all --search "<query>" --json number,title,state,labels,url
gh pr view <number> --json number,title,state,baseRefName,headRefName,mergeStateStatus,commits,files,url
```

This checkout's `gh` may not support `gh label`. For label reads, use:

```bash
gh api repos/0rl4nd0l/tenn/labels --paginate --jq '.[] | [.name, .description] | @tsv'
```

## Write Guard

Do not create, edit, label, comment on, close, reopen, push, or open PRs unless
the user has approved that exact GitHub write action or the current task card
explicitly requires and permits it.

Before proposing a new issue, search open and closed issues. Prefer updating or
commenting on the existing tracker when one already covers the work.

## Tenn Defaults

Use issue #78 for agent markdown and Codex repo documentation refresh work
unless live GitHub evidence shows a narrower tracker supersedes it.

For Financial Truth and extraction work, re-check the live issue family before
acting; older reports are background only.
