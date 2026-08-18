Issue #96 narrow persistence follow-up is complete in:

`reports/agent_jobs/extraction_empty_risk_note_suppression_v1_20260527/README.md`

Result: fixed the empty `ASXRiskNote` persistence bug by changing the financial-row path to call `_upsert_risk_note(..., allow_empty=False)`. Focused DB tests now prove empty no-narrative payloads create zero risk-note rows, while real narrative payloads still persist.

Validation: focused pytest passed (4 tests), py_compile passed, ruff passed, git diff check passed, task-card validation/check-diff passed.

No canary or broad backfill was run. No production DB/Qdrant/news/memory writes, parser routing changes, prompt changes, gold-label changes, source PDF changes, schema migrations, service restarts, runtime config changes, or canonical truth promotion changes were made.

Remaining DATA_MISSING: no second canary batch was run after this patch, orders 3-10 were not audited in this task, and no production cleanup was attempted for the already-created empty BHP risk-note row.
