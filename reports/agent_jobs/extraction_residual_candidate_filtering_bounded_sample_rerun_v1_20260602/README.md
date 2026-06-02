# Extraction Residual Candidate Filtering Bounded Sample Rerun V1

## Verdict

Runtime readiness was clean after minimal startup of the isolated backend health
surface and the local llama.cpp router. Redis queues were zero, no unacked keys
were present, only this registry job was active, and GPU process guard passed.

Exactly one bounded broad sample was run: count 8, seed 20260601, docs root
`/data/asx/docs`. No full extraction, broad backfill, canary, worker, direct SQL,
Qdrant, news, memory, source-PDF, prompt, or gold-label mutation was run.

## Result

Previous baseline: ok=3, failed=5.

Current result: ok=3, ok_low_confidence=1, failed=4.

Residual filtering modestly improved broad robustness by reducing failed results
from 5 to 4 and increasing non-failed results from 3 to 4. Strict ok count stayed
at 3, so this is not broad graduation evidence.

Candidate filter inventory also changed from the previous baseline:

- Previous retained: 23842
- Current retained: 22275
- Previous excluded: 4791
- Current excluded: 6358

## Failure Taxonomy

Failed documents:

- CQT postponement of quarterly results webinar: classifier_low_confidence; residual event/webinar scheduling update.
- AUK preliminary final report: validation_gate scale_validation:suspect_overscaled; formal report blocker.
- NCK FY21 results teleconference: validation_gate scale_unknown; residual results teleconference notice/presentation.
- CQT March quarterly activities report: validation_gate operational_update_without_formal_statements; quarterly activities update without formal statements.

Degraded non-failed document:

- RMS H1 FY results announcement and facility update: ok_low_confidence with 5 non-null metrics.

## Side Effects

Post-run state was clean: all five Redis queues were zero, no unacked keys were
present, no broad/backend/worker/llama process remained, GPU token was inactive,
GPU process guard showed no llama-server processes, and no source PDFs were
staged. The unrelated dirty file
`reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/diff-check.json`
was preserved untouched.

## Safety

Another random broad sample is not the safest next step yet. A narrow follow-up
sample or fixture pass targeting the residual non-candidate title classes and
the formal-report overscale gate is safer. Broad backfill/full extraction remains
blocked.

## DATA_MISSING

- API-visible loaded commit: `/api/version` returned 404 and `/api/health` only returned `{"status":"ok"}`.
- Clean task-card check-diff is blocked by pre-existing unrelated parity-guard report dirt outside this task.
