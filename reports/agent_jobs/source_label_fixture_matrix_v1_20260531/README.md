# Source Label Fixture Matrix v1

## Summary

Resolved GitHub issue #71 with a bounded tests/fixtures-only source-label
matrix.

## Scope

- Lane: Provenance.
- Branch: `safe/source-label-fixture-matrix-v1-20260531`.
- Worktree: `/home/l4nd0/tenn-source-label-fixture-matrix-v1-20260531`.
- Execution mode: SAFE EXTENSION.
- Product/runtime behavior changed: no.

## Files Added

- `financial-engine_v2/backend/tests/test_source_label_fixture_matrix.py`
- `cockpit-ui/lib/source-label-fixture-matrix.test.ts`
- `docs/agent_tasks/source_label_fixture_matrix_v1_20260531.md`
- `reports/agent_jobs/source_label_fixture_matrix_v1_20260531/`

## Fixture Coverage

Backend table-driven rows cover:

- live price source;
- historical financial source;
- weak local-news context;
- DATA_MISSING;
- no-hit;
- degraded runtime;
- memory context;
- external web context;
- unknown/unclassified snippet;
- direct claim-verified news event.

Frontend table-driven rows cover:

- Chat actionability states for direct claim verification, live price evidence,
  context-only historical sources, weak news context, DATA_MISSING, no-hit,
  degraded runtime, memory context, external web context, and unknown
  snippet-only context.
- Home trust label actionability for claim-verified, context-only,
  DATA_MISSING, degraded-runtime, demo, and unknown unresolved source rows.

## Boundaries Preserved

No changes were made to:

- source-label semantics;
- product behavior;
- backend routes or services;
- frontend production components/helpers;
- canonical financial truth;
- parser or extraction routing;
- extraction prompts;
- gold labels;
- production data;
- DB, Qdrant, news, or memory stores;
- runtime, model, GPU, service, scheduler, or provider config.

## Validation

- Task-card validate: PASS.
- Registry check-overlap: PASS.
- Registry claim: PASS.
- Backend focused test:
  `PYTHONPATH=/home/l4nd0/tenn-source-label-fixture-matrix-v1-20260531/financial-engine_v2/backend /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/pytest financial-engine_v2/backend/tests/test_source_label_fixture_matrix.py`
  PASS, 20 passed.
- Python lint:
  `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.venv/bin/ruff check financial-engine_v2/backend/tests/test_source_label_fixture_matrix.py`
  PASS.
- Frontend focused test:
  temporary `node_modules` symlink to the existing clean checkout dependency
  install, then `./node_modules/.bin/vitest run lib/source-label-fixture-matrix.test.ts`
  PASS, 16 passed.
- Frontend lint:
  temporary `node_modules` symlink to the existing clean checkout dependency
  install, then `./node_modules/.bin/eslint lib/source-label-fixture-matrix.test.ts`
  PASS.

## DATA_MISSING

- `graphify-out/wiki/index.md` and `graphify-out/GRAPH_REPORT.md` are absent
  in this worktree, so graphify community/god-node context could not be
  inspected.

## Close Gate

Issue #71 is ready to close after commit/push because the required bounded
source-label fixture matrix is present, table-driven, validation-backed, and
does not alter source-label semantics or product/runtime behavior.
