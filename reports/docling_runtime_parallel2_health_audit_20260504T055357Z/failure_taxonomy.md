
# Failure Taxonomy

## Verdict

Primary classification: `failure_mode_classified_request_timeout` with confirmed runtime-health instability and partial-payload leakage risk. Concurrent document extraction remains blocked. Cell C timing is invalid and must not be described as a speedup.

## Taxonomy

| Failure mode | Classification | Evidence | Scoring impact | Guardrail |
| --- | --- | --- | --- | --- |
| Runtime port open while `/health` false | `failure_mode_classified_runtime_health` | `23` samples in `request_health_timeline.csv` / `runtime_health_timeline.csv`; first `2026-05-04T05:16:46.483150+00:00`, last `2026-05-04T05:28:31.947498+00:00` | Runtime was not a clean extraction substrate during Cell C; timing cannot be trusted | Fail fast or quarantine the diagnostic cell on any active `port_open=true` + `health_ok=false` sample |
| Llama request timeout at 120s | `failure_mode_classified_request_timeout` | `4` captured `llm_request_timings` errors: bhp_a_2025-06-30, qbe_h_2025-06-30, rio_a_2023-12-31 | Timeout occurred inside per-table LLM calls and may not appear as document-level `extraction_error` | Gate on request-level timing errors, not only document-level extraction errors |
| Slot contention | `failure_mode_inconclusive` | `/slots` probe had `53` timeout samples, but slot/task IDs are not mapped to document IDs | Slot pressure is plausible but not proven from current artifact shape | Capture slot/task ID, prompt/call index, and document ID correlation before classifying |
| Partial payload after failed LLM call | `failure_mode_classified_partial_payload` | Pass 3a catches failed table LLM calls, retries truncated, and can continue without that table result | Metrics/trust can be scored against an incomplete payload; QBE missed `net_debt` and trust abstained | Harness should quarantine/fail the cell on any captured request timeout before scoring/timing comparison |
| Source experiment health provenance gap | `failure_mode_classified_runtime_health` for diagnostic artifact; source harness gap | Artifact-local `diagnostic_driver.py` recorded health timeline, while `scripts/run_docling_parallel2_experiment.py` did not poll health during Cell C | Future source-harness runs could miss transient health-false states | Add diagnostic-only runtime-health timeline and active-run fail-fast before any promotion run |

## Boundary

No production extraction semantics were changed. Trust semantics, prompts, gold labels, metric normalization, routing, timeout values, and llama runtime settings remain out of scope.
