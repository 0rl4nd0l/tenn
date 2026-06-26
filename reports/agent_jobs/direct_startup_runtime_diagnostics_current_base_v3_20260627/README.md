# Direct Startup Runtime Diagnostics Current-Base V3

Issue: #280
Branch: `safe/issue280-direct-startup-diagnostics-current-base-v3-20260627`
Base: `origin/migration/clean-runtime-baseline-reconstruct-v1@b58ec5a047f6b6bd42c4d567c299e6e9601c5225`

## Result

`DONE_WITH_RISK`: diagnostics implementation and focused validation are
complete. Live backend startup was not run, so runtime functionality is not
proven.

## Scope

- Added pure startup diagnostics helper for entrypoint label, DB URL class, and
  effective feature flags.
- Expanded backend runtime config logging to include entrypoint, DB class,
  auto-create setting, embeddings, Qdrant, and extraction state.
- Added a warning for direct/unknown startup when production-like settings are
  active.
- Marked canonical `run_local_backend.sh` startup with
  `TENN_BACKEND_ENTRYPOINT=run_local_backend`.
- Added focused tests for diagnostics behavior and the script marker.

## Safety

No service starts, DB/Redis/Qdrant/news/memory/source-PDF/gold-label/model
mutation, runtime config mutation, default feature flag changes, fail-fast
behavior, or Cockpit/frontend changes were performed.

## Prior Work

The stale worktree
`/home/l4nd0/tenn-issue280-direct-startup-diagnostics-v1-20260626` was used as
preserved evidence only. It was not mutated. The useful diff was ported onto
current canonical in this worktree.
