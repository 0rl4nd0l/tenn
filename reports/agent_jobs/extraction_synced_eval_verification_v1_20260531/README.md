# Extraction Synced Eval Verification

Generated: 2026-05-31T06:33:27Z

This report preserves current-turn, non-runtime evidence for the full metric
extraction hardening objective after the metric ontology gate slice.

## Scope

- Lane: Evaluation, supporting Financial Truth.
- Worktree: `/home/l4nd0/tenn-extraction-metric-ontology-gate-v1-20260531`.
- Branch: `safe/extraction-metric-ontology-gate-v1-20260531`.
- HEAD: `fd65cef787e9`.
- Origin baseline: `origin/migration/clean-runtime-baseline-reconstruct-v1` at
  `5b276e4ba9aa`.
- Branch relation to origin baseline: `0` behind, `2` ahead.
- Contested surfaces touched: none.

## Evidence

- Shared baseline `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
  remains at `7ee06fbdad5f` and is still `0` ahead / `8` behind origin.
- The isolated branch includes the merged PR #129 origin baseline and adds the
  metric ontology gate commits on top.
- Focused real-gold/scorecard/ontology/pre-canary/capability pytest passed:
  `108 passed, 6 warnings`.
- Broader extraction evaluation lane pytest passed:
  `388 passed, 1 deselected, 6 warnings`.

## What This Proves

- PR #129's merged origin baseline is locally testable in the isolated branch.
- The metric ontology gate slice did not break the broader non-runtime
  extraction evaluation lane covered by the selected tests.
- Pre-persistence scorecard and ontology hardening remain evaluation-local and
  do not authorize canonical writes.

## What This Does Not Prove

- It does not sync the shared baseline branch.
- It does not run, authorize, or satisfy the third canary.
- It does not prove full accurate extraction graduation.
- It does not prove runtime health, queue health, loaded runtime code, or source
  path readiness.

## Boundaries

No backend, worker, llama, Docker, GPU service, canary, runtime extraction,
backfill, DB, Qdrant, source-PDF, parser, prompt, schema, Cockpit UI, GitHub, or
canonical-truth mutation was performed.
