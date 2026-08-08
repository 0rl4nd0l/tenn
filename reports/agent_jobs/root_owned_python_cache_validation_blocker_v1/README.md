# Root-Owned Python Cache Validation Blocker

Issue: https://github.com/0rl4nd0l/tenn/issues/140

## Decision

`KEEP_OPEN_DATA_MISSING`.

This job is report-only. It preserves the current inventory and cleanup decision for the shared checkout, but it does not remove, chown, quarantine, or rewrite any ignored `__pycache__` directory.

## Current Evidence

- Shared checkout inspected: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- Isolated report worktree: `/home/l4nd0/tenn-root-owned-python-cache-validation-blocker-audit-v1-20260601`
- Duplicate PR search for `140 OR root-owned Python cache OR compileall PermissionError OR __pycache__ validation writes` returned no PRs.
- Current shared registry has an active Financial Truth job: `extraction_real_gold_eval_current_head_runtime_v1_20260601`.
- The active job owns the same shared worktree that contains the root-owned cache directories.
- Current inventory found 19 root-owned ignored Python cache directories under `financial-engine_v2/`.

## Cleanup Decision

Cleanup is deferred.

The issue is real, but the safe mutation point is after the active Financial Truth job releases the shared checkout. Removing or owner-repairing generated directories while another validation/runtime job owns that checkout would create avoidable interference risk.

## Validation Impact

Focused compile/write validation was not run in this job because the root-owned cache repair was not performed. That validation remains the acceptance gate after cleanup:

```bash
python3 -m compileall financial-engine_v2/backend/app financial-engine_v2/cockpit financial-engine_v2/shared
```

## DATA_MISSING

- Cleanup result after the active Financial Truth job releases.
- Focused compile/write validation after cleanup or owner repair.
- Proof that no root-owned ignored source-tree `__pycache__` directories remain after cleanup.
- Final decision between removal and owner repair.

## No-Mutation Attestation

- No tracked product/backend/frontend/runtime code changed.
- No DB, Qdrant, news, memory, canonical financial truth, parser routing, extraction prompt, gold label, runtime/model/GPU/service config, or service process was changed.
- No cache directory was removed, chowned, quarantined, or rewritten.
- No broad cleanup command such as `git clean -X` was run.

## Next Safe Step

After `extraction_real_gold_eval_current_head_runtime_v1_20260601` releases, run a scoped cleanup task that removes or owner-repairs only the inventoried ignored generated directories, proves tracked files are untouched, and runs the focused compile/write validation.
