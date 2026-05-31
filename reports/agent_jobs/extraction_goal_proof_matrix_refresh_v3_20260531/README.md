# Extraction Goal Proof Matrix Refresh V3

Generated: 2026-05-31T06:49:58Z

This report refreshes the full 10-item metric extraction hardening objective
after the metric ontology gate, synced local eval verification, and runtime
approval-preflight slices.

## Verdict

Status: PARTIAL. The full objective remains open.

The merged PR #129 baseline is locally testable on the isolated branch, metric
ontology / pre-persistence gates are stronger, and the broader non-runtime
extraction evaluation lane passes. The third canary has still not run, backend
and queue endpoints are still unreachable, and full accurate extraction remains
unproven.

## Current Evidence

- Isolated branch: `safe/extraction-metric-ontology-gate-v1-20260531`.
- Isolated HEAD: `1bca673212b1`.
- Isolated relation to `origin/migration/clean-runtime-baseline-reconstruct-v1`:
  `0` behind / `4` ahead.
- Shared baseline remains at `7ee06fbdad5f`, `0` ahead / `8` behind origin,
  with unrelated untracked Query Orchestration task-card state.
- PR #129 is merged with green `lint-and-test` and `scan`.
- Current extraction evaluation lane: `388 passed, 1 deselected, 6 warnings`.
- Backend `/api/health` and `/api/queue/status`: connection refused,
  `HTTP_STATUS:000`.
- Direct `nvidia-smi`: succeeds; Tesla M40 reports `0` MiB used.
- `scripts/gpu_process_guard.sh --check`: exit `0`.
- All seven prior eligible third-canary source PDFs are present.

## Current 10-Item Summary

1. Truth-gate patch: partial; merged remotely and present in isolated branch,
   but shared baseline remains unsynced.
2. Advisory blocking upstream: proven for current baseline scope.
3. Source document classification: proven for current baseline scope.
4. Scale Policy V1: proven for current policy slice; FX remains out of scope.
5. Metric ontology: proven for current eval-gate scope, not runtime graduation.
6. Period semantics: proven for current AAU blocker scope.
7. Real gold/eval corpus: proven for current local eval scope on isolated
   branch; shared baseline still unsynced.
8. Pre-persistence scorecard gates: proven as report-local/eval-local gates;
   no approved canary payload has been scored yet.
9. Third canary under approval: blocked before execution.
10. Full accurate extraction: not proven.

## Boundaries

No backend, worker, llama, Docker, GPU service, canary, runtime extraction,
backfill, DB, Qdrant, source-PDF, parser, prompt, schema, Cockpit UI, GitHub, or
canonical-truth mutation was performed.
