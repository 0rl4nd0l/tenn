# State

- Branch: `safe/issue240-intel-pulse-api-key-current-base-v1-20260627`
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Issue: #240
- Replacement PR: https://github.com/0rl4nd0l/tenn/pull/450
- Current head: `b370abef8d6a6e31654eaee3b4a4bd7ba9757046`
- Superseded prior work: PR #435 is conflicting on current base and has a P2
  review finding about browser-stored Cockpit API keys.

## GitHub State

- PR #450 is open and non-draft.
- `mergeable`: `MERGEABLE`
- `mergeStateStatus`: `UNSTABLE`
- Checks at last read:
  - `scan`: success
  - `lint-and-test`: in progress
- Issue #240 is not closed. Closeout requires green checks, no unresolved
  review blockers, and canonical containment evidence after merge.

## Changes

- Added `require_api_key` dependencies to `/api/cockpit/pulse` and
  `/api/cockpit/matrix`.
- Updated the shared Cockpit API client key helper to prefer browser
  `localStorage["cockpit.apiKey"]` before `NEXT_PUBLIC_API_KEY`.
- Sent `X-API-Key` from `getIntelPulse()` and `getDiagnosticMatrix()`.
- Added focused backend and frontend regressions.
- Documented guarded Intel Pulse route policy.

## Safety

- No DB, Qdrant, news store, memory store, source PDF, gold label, extraction
  prompt, runtime service, model, GPU, or production data mutation was performed.
- Intel Pulse service semantics and diagnostic matrix cell-state logic were not
  changed.
- Local pre-push hook was bypassed with `TENN_ALLOW_MISSING_HOOK_TOOLS=1`
  because the worktree venv lacked hook-local `ruff` and `pytest`; equivalent
  focused checks passed through `uv run` before push.
