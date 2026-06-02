# Extraction Residual Failure Gate Bounded Sample Rerun V1

## Verdict

Runtime readiness was clean after minimal isolated backend startup and local llama.cpp router startup. Redis queues were zero, no unacked keys were present, no overlapping registry job was active, and GPU guard passed.

Exactly one bounded broad sample was run: count 8, seed 20260601, docs root `/data/asx/docs`. No full extraction, broad backfill, worker, direct SQL, Qdrant, news, memory, source-PDF, prompt, or gold-label mutation was run.

## Result

Previous post-filtering baseline: ok=3, ok_low_confidence=1, failed=4.

Current result: ok=4, ok_low_confidence=0, failed=4.

Residual failure-gate hardening modestly improved the strict-ok count from 3 to 4 and removed the low-confidence result, but failed count stayed at 4. This is not broad graduation or backfill evidence.

Candidate filter inventory versus the previous post-filtering sample:

- Previous retained: 22275
- Current retained: 21174
- Previous excluded: 6358
- Current excluded: 7459
- Additional exclusions after hardening: 1101

## Failure Taxonomy

Failed documents:

- AZJ half-year FY2023 results: validation_gate insufficient_metrics:1; real half-year results release, extraction coverage gap.
- ABE annual report 2022: validation_gate scale_unknown; real annual report, scale evidence unresolved.
- CRS base metals drilling results: validation_gate non_financial_update_without_formal_statements; non-financial exploration update admitted by candidate selection then blocked by source-class gate.
- WBC FY2023 notable items: validation_gate insufficient_metrics:1; pre-results notable-items announcement, not the formal full-year report.

Low-confidence cases: none.

## Side Effects

Post-run state was clean: all five Redis queues were zero, no unacked keys were present, no broad/backend/worker/llama process remained, GPU token was inactive, GPU process guard showed no llama-server processes, and no source PDFs were staged. The unrelated dirty file `reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/diff-check.json` was preserved untouched.

## Safety

Another random broad sample is not justified as the next step. The safe next step is a narrow audit/hardening pass for the new residual source classes, especially exploration assay/results updates and notable-items pre-results announcements, plus targeted scale/coverage diagnostics for real reports. Broad backfill/full extraction remains blocked.

## DATA_MISSING

- API-visible loaded commit: `/api/version` returned 404 and `/api/health` only returned `{"status":"ok"}`.
- Clean task-card check-diff remains blocked only by the pre-existing unrelated parity-guard report dirt outside this task.
