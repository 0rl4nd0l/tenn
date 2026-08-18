# State

state: VALIDATING

## Current Evidence

- Worktree:
  `/home/l4nd0/tenn-opencode-worker-bridge-safety-fix-v1-20260618`
- Branch: `control-plane/opencode-worker-bridge-safety-fix-v1-20260618`
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Base commit at worktree creation:
  `e555f540019a50462da1596a6c2986260468b4d8`
- PR #370 state: `MERGED`

## Duplicate Work

- Registry active-job check found one unrelated extraction job.
- Live task ledger: `DATA_MISSING`.
- Durable task ledger: `DATA_MISSING`.
- Fallback search found PR #370 as merged prior work and no active/new bridge
  safety-fix PR.

duplicate_work_classification: SUPERSEDED_IGNORE for prior PR #370 review fix;
continue with this post-merge safety follow-up.

## Implementation

- `evidence_only` workers now fail closed when `OPENCODE_SERVER_URL` would
  trigger attach mode without proven remote readonly enforcement.
- Worker metadata records `attach_mode_requested`, `attach_mode_allowed`, and
  `remote_permission_verified`.
- Result validation accepts an expected/requested `decision_limit` and rejects
  worker output that reports a different limit.
- `command_run` passes its requested `decision_limit` into result validation.

## Unsafe Actions Avoided

- No changes in the dirty ledger checkout.
- No product/runtime/data/extraction/count-24 edits.
- No host-global mutations.
- No dependency or lockfile edits.
