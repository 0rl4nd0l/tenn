# Action Matrix Applied

Applied from the Phase 3F plan:

- `COMMIT_TO_BASELINE_CANDIDATE`: Phase 2 schema/fixtures, Phase 3A adapter docs, Phase 3B reconciled vectors/payloads/test, and Phase 3C mock transport docs/fixtures/test.
- `FORCE_ADD_REPORT_EVIDENCE_CANDIDATE`: exact report-child files listed in the active Phase 3G task card.
- Task-history evidence: Phase 2 through Phase 3G task cards listed in the active task card.

Refinement applied during validation:

- Reconciled Phase 3B mock payloads superseded the older Phase 3A payload copies because the Phase 3B unittest expects required artifact flags in `mock_missing_benchmark_result_v1.json`.
- Phase 3B and Phase 3C mock payload directories were identical, so Phase 3B was used as the stable reconciled source.

Explicitly not applied:

- Phase 2B helper runtime/backend files.
- Older duplicate `strategy_lab_quantdinger_framework_v1_20260520` report bundles.
- Generated `__pycache__` or `.pyc` files.
- Cockpit files or shared dirty Cockpit task cards.
