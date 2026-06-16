# Agent Task Ledger

The Agent Task Ledger is the duplicate-work prevention backbone for Tenn
implementation-capable agent sessions.

## Sources

- Live branch-independent ledger:
  `<git-common-dir>/tenn-agent-registry/task-ledger.jsonl`
- Durable committed snapshot:
  `docs/agent_registry/task_ledger/LEDGER.md`
  `docs/agent_registry/task_ledger/LEDGER.jsonl`

The live ledger is host/repo-local and shared by worktrees attached to the same
git common dir. Linked worktrees have private git dirs, so agents must not
resolve the live ledger through a literal `.git/tenn-agent-registry` path. Use
`git rev-parse --path-format=absolute --git-common-dir` when available, or
normalize `git rev-parse --git-common-dir` output against the worktree root when
the absolute path option is unsupported. The committed snapshot is a periodic
summary for future agents and is not expected to be complete immediately.

## Required Preflight

Before non-trivial implementation, agents should check:

- live ledger
- committed ledger when present
- task cards
- reports
- branches
- worktrees
- open and merged PRs
- related issues
- files likely to be touched

If ledger sources are unavailable, record `DATA_MISSING` and perform the bounded
fallback search before coding.

## Classifications

- `ACTIVE_CONTINUE`: continue or adopt active work.
- `OPEN_PR_WAIT`: wait for or review the open PR.
- `MERGED_USE_CANONICAL`: use merged canonical work.
- `STALE_PRESERVE`: preserve, park, or intentionally supersede stale work.
- `SUPERSEDED_IGNORE`: older work can be ignored because current canonical state
  supersedes it.
- `OWNER_BOUNDARY`: Orlando must decide before proceeding.
- `UNKNOWN_ASK`: evidence is insufficient for a safe implementation decision.

## Status Values

Use these status values for implementation-capable sessions:

- `claimed`
- `implementation_started`
- `blocked`
- `waiting_on_user`
- `pr_opened`
- `merged`
- `done`
- `parked`
- `superseded`

No script implementation is included here. Use
`docs/dev_flow/templates/TASK_LEDGER_ENTRY.json` and
`docs/dev_flow/templates/TASK_LEDGER_SUMMARY.md` as the initial write and
summary shapes.
