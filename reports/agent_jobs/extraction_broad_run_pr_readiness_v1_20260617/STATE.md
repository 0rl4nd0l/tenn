# State

Status: `DONE_WITH_RISK`

## Branch State

Branch:
`safe/extraction-broad-run-provenance-risk-flags-v1-20260617`

Base:
`origin/migration/clean-runtime-baseline-reconstruct-v1`

Reviewed commits:

- `deba6e0b feat(extraction): surface broad-run provenance risk flags`
- `a0b54e66 test(extraction): replay broad-run provenance fixture`
- `4f58d1b7 test(extraction): add positive scale risk fixture`

## Scope

Changed files relative to base:

- `financial-engine_v2/scripts/broad_extraction_test.py`
- `financial-engine_v2/scripts/test_broad_extraction_test.py`
- three task cards under `docs/agent_tasks/`
- three report bundles under `reports/agent_jobs/`

## Task Ledger

- Live ledger: `DATA_MISSING`
- Committed ledger: `DATA_MISSING`
- Current ledger status: `DATA_MISSING`
- Ledger update result: `DATA_MISSING`
- Duplicate-work classification: `CONTINUE_LOCAL_PR_READINESS`

## Readiness State

Local review decision: `pass_with_risk`

The branch is coherent and focused enough for owner-authorized PR publication.
This task card does not authorize push or PR creation.

## Residual Risk

- No live broad extraction, count-24/count-32, or runtime validation was run by
  design.
- Report fixtures validate shape and helper behavior, not real-document
  universe coverage.
- Push and PR are intentionally still outside this task card.
