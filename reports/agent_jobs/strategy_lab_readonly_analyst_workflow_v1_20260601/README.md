# Strategy Lab Readonly Analyst Workflow

Issue: #76, `[Strategy Lab] Convert QuantDinger from infrastructure proof into analyst-useful read-only workflow`

## Decision

Implement a narrow library/API-contract slice. The existing Strategy Lab
artifacts route already returns `review_workflow`; this task adds analyst-useful
read-only workflow definitions to that object without adding runtime transport,
Home layout, backend, database, Qdrant, memory, or execution behavior.

## Implemented Change

- Added `analyst_workflows` to the Strategy Lab review workflow contract.
- Added four repo-only workflows:
  - interpret an existing QuantDinger backtest artifact.
  - compare repeatability and re-probe outputs.
  - explain a saved regime result and its limits.
  - attach QD evidence to a strategy idea as pending review.
- Each workflow preserves `PENDING_REVIEW`, `source_mode=repo_artifacts_only`,
  `current_sidecar_available=false`, `execution_allowed=false`,
  `canonical_financial_truth=false`, and `real_transport=false`.
- Focused tests assert the workflow IDs, read-only output, and deny-boundary
  flags.

## Safety

- Reporting lane, safe extension mode.
- No Home files touched.
- No backend, data, extraction, retrieval, memory, financial truth, runtime,
  sidecar probing, schema, or store-write changes.
- No current QuantDinger availability, execution, paper trading, live trading,
  or canonical truth promotion is claimed.

## Validation Notes

- Task card validation, registry claim, and overlap check passed.
- Focused Strategy Lab artifact Vitest passed: 1 file, 3 tests.
- Focused ESLint passed on the touched Strategy Lab files.
- JSON validation, path-redaction scan, and diff checks are part of closeout.

## Remaining Scope

This creates the bounded analyst workflow contract. It does not build a new
route-specific UI page, live adapter, current sidecar check, review decision
store, or promotion workflow.
