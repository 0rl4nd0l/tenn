# Agent Task Ledger

The Agent Task Ledger is the duplicate-work prevention backbone for Tenn
implementation-capable agent sessions.

## Sources

- Live branch-independent ledger:
  `<registry_root>/task-ledger.jsonl`
- Durable committed snapshot:
  `docs/agent_registry/task_ledger/LEDGER.md`
  `docs/agent_registry/task_ledger/LEDGER.jsonl`

The live ledger is host/repo-local and shared through the same registry root as
`scripts/agent_job_registry.py`. Linked worktrees have private git dirs, so
agents must not resolve the live ledger through a literal `.git/tenn-agent-registry`
path. Resolve `<registry_root>` in this order:

1. `TENN_AGENT_REGISTRY_ROOT`
2. `git config tenn.agentRegistryRoot`
3. `git rev-parse --path-format=absolute --git-common-dir` plus
   `tenn-agent-registry`
4. normalized `git rev-parse --git-common-dir` plus `tenn-agent-registry` when
   the absolute path option is unavailable
5. repo-local fallback with a warning when git metadata is unavailable

The committed snapshot is a periodic summary for future agents and is not
expected to be complete immediately.

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
