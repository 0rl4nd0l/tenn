# WORKER_RESULT_GIT_HYGIENE_SESSION_TRACE

Status: DONE_WITH_RISK

## Evidence

- Worktree: `/home/l4nd0/tenn-agent-ledger-runtime-handoff-v1-20260617`
- Branch: `control-plane/agent-ledger-runtime-handoff-v1-20260617`
- HEAD/base/merge-base: `6eff52404af61b9717bffb5a250e06209713d517`
- Upstream: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Registry read-only: OK, `active_jobs: []`

## Session Discovery

Use explicit safe sources only:

1. `CODEX_THREAD_ID`, `TENN_AGENT_SESSION_ID`, `CODEX_SESSION_ID`,
   `CLAUDE_SESSION_ID`.
2. Read-only `~/.codex/goals_1.sqlite` lookup keyed by explicit
   `CODEX_THREAD_ID`.
3. Explicit hook or handoff payload fields.
4. Otherwise write `DATA_MISSING`.

Do not treat `hostname:pid:job_id` registry lease fallback IDs as Codex
thread/session IDs.

## Ledger Path Risk

This is a linked worktree. The live ledger must be
`<registry_root>/task-ledger.jsonl`, not literal worktree
`.git/tenn-agent-registry/task-ledger.jsonl`.

## DATA_MISSING

- Current Codex session ID: `DATA_MISSING`
- Live task ledger: `DATA_MISSING`

## Recommendation Applied

Keep session/thread fields required but allow `DATA_MISSING`. Resolve the live
path via `agent_job_registry.resolve_registry_location`.
