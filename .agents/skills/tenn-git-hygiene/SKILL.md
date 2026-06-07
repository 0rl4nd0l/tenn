---
name: tenn-git-hygiene
description: Use for Tenn-native Git hygiene control-plane work: safely inspecting, classifying, preserving, integrating, and recommending cleanup for Tenn branches, worktrees, dirty files, stale uncommitted work, merge/rebase candidates, and report-only Scribe or Watcher ledgers without mutating Git or GitHub unless explicitly approved.
---

# Tenn Git Hygiene

Use this skill for Tenn development workflow and control-plane Git hygiene only.
It is not Tenn product, backend, frontend, runtime, data, extraction, model, GPU,
prompt, source-PDF, gold-label, DB, Qdrant, news, memory, service, or backfill
work.

## Core Rule

Git hygiene is report-first and approval-gated. Dirty work older than 24h is not
trash. It is unclassified work requiring preservation, ownership, or a disposal
decision.

Never create a persistent mutating agent. A Scribe or Watcher may maintain
ledgers and recommendations, but must not clean, stash, reset, rebase, merge,
cherry-pick, delete, push, mutate GitHub, mutate registry state, or change
product/runtime/data files.

## Modes

- `AUDIT_ONLY`: read-only inventory and classification only.
- `REPORT_LOCAL`: write ledger, report, and task-card artifacts only.
- `PRESERVE_ONLY`: create a patch bundle, exact allowlisted preservation commit,
  or archival branch only after explicit approval.
- `INTEGRATE_APPROVAL_REQUIRED`: merge, rebase, cherry-pick, PR, or GitHub
  action only after explicit approval.
- `CLEANUP_APPROVAL_REQUIRED`: branch deletion, worktree removal, `git clean`,
  `git reset --hard`, stash drop, archive deletion, or remote branch deletion
  only after explicit approval.

Default to `AUDIT_ONLY`. Move to `REPORT_LOCAL` only when the user asks for a
report, ledger, or task card. Higher modes require explicit approval in the
current conversation and an exact allowlist.

## Safety Tiers

- Tier 0: read-only commands such as `pwd`, `git status`, `git branch`,
  `git worktree list`, `git log`, `git diff`, `git show`, `git ls-remote`, and
  read-only `gh` inspection.
- Tier 1: report-local writes such as task cards, ledgers, audit reports, and
  recommendations.
- Tier 2: preservation actions such as patch bundles, exact allowlisted
  preservation commits, or archival branches.
- Tier 3: integration actions such as merge, rebase, cherry-pick, PR creation,
  PR update, or GitHub comments.
- Tier 4: destructive actions such as branch deletion, worktree removal,
  `git clean`, `git reset --hard`, stash drop, force-push, or remote branch
  deletion.

Tier 0 is always safe if commands are genuinely read-only. Tier 1 requires a
task card and allowlist. Tiers 2-4 require explicit approval, rollback notes,
and focused validation.

## Hard Boundaries

- Do not touch product, backend, frontend, runtime, data, extraction, model,
  GPU, prompt, source-PDF, gold-label, DB, Qdrant, news, memory, services,
  production data, or backfills.
- Do not install dependencies.
- Do not push unless explicitly approved.
- Do not create, edit, close, comment on, or label GitHub issues or PRs unless
  explicitly approved.
- Do not run `git clean`, `git reset --hard`, `git stash drop`, branch deletion,
  worktree removal, rebase, merge, cherry-pick, force-push, or remote branch
  deletion unless the mode and approval explicitly allow it.
- Do not clean or modify existing dirty worktrees to make the audit easier.
- Do not widen a task-card allowlist to absorb unrelated dirt.

## Required Preflight

Run these before classification or recommendations:

```bash
pwd
git remote -v
git branch --show-current
git rev-parse HEAD
git status --short --untracked-files=all
git worktree list --porcelain
git branch -vv --no-abbrev
python3 scripts/agent_job_registry.py list-active --read-only --repo-root .
```

When GitHub state matters, add read-only `gh` evidence, for example:

```bash
gh pr list --state open --json number,title,headRefName,baseRefName,isDraft,mergeStateStatus,updatedAt
gh pr view <number> --json number,title,headRefName,baseRefName,headRefOid,baseRefOid,mergeStateStatus,isDraft,updatedAt,files
gh issue list --state open --json number,title,state,updatedAt,labels
gh issue view <number> --json number,title,state,updatedAt,labels,body
```

If a required command is unavailable or not safely read-only, record
`DATA_MISSING` and keep the mode at `AUDIT_ONLY` or `REPORT_LOCAL`.

## Dirty Work Age Classification

Classify dirty and untracked work by best available evidence: file mtimes,
branch commit dates, task cards, reports, registry records, chat handoffs, and
worktree naming. Do not infer deletion safety from age alone.

- `<24h`: active / current.
- `1-3d`: inspect and preserve candidate.
- `3-7d`: decision needed.
- `>7d`: archive, patch, branch, or closeout candidate.
- unknown age: `DATA_MISSING`.

For every dirty group, report owner, likely intent, age class, paths, branch,
worktree, evidence, risk, and recommended next action.

## Classification Outputs

For branches, classify as one of:

- current target branch
- active implementation
- report-only/audit
- preservation candidate
- integration candidate
- stale but valuable
- superseded candidate
- cleanup candidate
- protected/canonical/shared
- `DATA_MISSING`

For worktrees, classify as one of:

- active execution surface
- clean review surface
- dirty owned work
- dirty ambiguous ownership
- prunable metadata only
- archival evidence
- unsafe to touch
- `DATA_MISSING`

For dirty files, classify as one of:

- task-card/report-local artifact
- product/runtime/data/extraction surface
- generated artifact
- source evidence
- validation output
- user-owned unknown
- stale preservation candidate
- cleanup candidate requiring approval
- `DATA_MISSING`

## Merge, Rebase, And Cherry-Pick Rules

Prefer merge or PR for shared, pushed, reviewed, or multi-commit work. Rebase
only for local/private branches with clean worktree, recorded rollback ref, and
explicit approval.

Before merge, rebase, or cherry-pick, write an Integration Plan containing:

- source branch/worktree and exact SHA
- target branch and exact SHA
- merge base
- ahead/behind counts
- changed files and staged files
- overlap with target and current dirty work
- conflict risk from `git merge-tree` or equivalent read-only evidence
- protected/shared branch risk
- rollback plan, including rollback ref or branch
- validation plan and expected commands
- approval needed and exact action to approve

Never rebase canonical, protected, pushed shared, reviewed, or multi-owner
branches without explicit approval. Never force-push without explicit approval.
If approval is absent, stop at the Integration Plan.

## Scribe / Watcher Pattern

A Scribe or Watcher is report-only. It may inspect chats, handoffs, reports,
task cards, branches, worktrees, GitHub state, and ledgers. It may maintain:

```text
WORKTREE_LEDGER.md
BRANCH_LEDGER.md
DIRTY_WORK_LEDGER.md
RECOMMENDATIONS.md
```

It must not mutate Git state, GitHub, registry, product files, runtime state, or
data. It must not clean, stash, reset, rebase, merge, cherry-pick, delete, push,
or force-push.

Interrupt only for high-risk stale dirty work, ambiguous ownership, conflicting
branches, protected-branch risk, or possible data loss. Otherwise, report
recommendations and keep operating in `AUDIT_ONLY` or `REPORT_LOCAL`.

## Report Requirements

Every report must include:

- objective
- mode and safety tier
- files changed
- exact skill summary
- safety tiers
- Scribe boundaries
- approval gates
- preflight evidence
- dirty work age classification
- branch/worktree/file classification
- Integration Plan when integration is being considered
- validation commands and exit status
- `DATA_MISSING`
- unsafe actions avoided
- next recommended report-only Git hygiene audit prompt

If approval is needed, include:

```text
WAITING_ON_USER
Needed: <exact approval>
Why: <what this unlocks>
Current safe state: <what was inspected or written>
Recommended: <one bounded next action>
```

## Validation

For skill/report/task-card edits, run:

```bash
python3 scripts/agent_job_contract.py validate <task-card>
python3 scripts/agent_job_contract.py check-diff <task-card> --no-write-report
git diff --check
git status --short --untracked-files=all
```

Also parse skill frontmatter for `name` and `description`. If validation fails
because of unrelated existing dirt, record the blocker and do not clean or widen
the allowlist. If validation would require runtime or production data access,
record it as out of scope.
