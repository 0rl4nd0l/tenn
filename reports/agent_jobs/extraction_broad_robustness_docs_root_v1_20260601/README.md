# Extraction Broad Robustness Docs Root V1

## Summary

This safe-extension slice unblocks broader extraction robustness evidence by
making `financial-engine_v2/scripts/broad_extraction_test.py` use the active
ASX docs root instead of only the empty repo-local docs tree.

The helper now supports `--docs-root`, respects `DOCS_ROOT` and
`DATA_ROOT/asx/docs`, falls back to `/data/asx/docs`, and records external PDFs
as stable `data/asx/docs/...` identifiers so resume/report artifacts stay
portable across the host-root and repo-root layouts.

## Evidence

- Repo-local financial-performance PDFs:
  `0` under `financial-engine_v2/data/asx/docs`.
- Host financial-performance PDFs:
  `28,633` under `/data/asx/docs`.
- Default resolver after this change:
  `/data/asx/docs`.
- Focused test suite:
  `5 passed`.

## Boundaries

- Broad extraction run: false.
- Runtime/backend/router/worker startup: false.
- Database, Qdrant, news, memory, or canonical financial row mutation: false.
- Source PDF copy or mutation: false.
- Parser, prompt, schema, or model/GPU config change: false.
- Cockpit UI or GitHub mutation: false.

## Full Goal Status

This moves the full metric-extraction objective forward by removing a concrete
blocker to broader robustness sampling. It does not prove broad extraction
accuracy, run a canary/backfill, authorize persistence, or complete
full ticker-universe graduation.
