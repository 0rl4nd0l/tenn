
# Health Audit Summary

## 1. Lane Classification

Lane: Financial Truth. This is an audit plus diagnostic-harness-only safe extension. Concurrent document extraction remains blocked.

## 2. Collision Assessment

Collision risk is elevated because the worktree already had unrelated modified files before this audit. This lane changed only `scripts/run_docling_parallel2_experiment.py`, added `scripts/test_run_docling_parallel2_experiment.py`, and created this report directory. No production extraction service, prompt, gold, trust, metric-normalization, routing, fallback, timeout, or llama runtime setting was changed.

## 3. Execution Mode

Mode: AUDIT first, then SAFE EXTENSION limited to harness-level timeout classification. No broad parallel extraction was run. The dedicated stopped `:8002` runtime was not restarted.

## 4. Failure Mode Classification

Primary: `failure_mode_classified_request_timeout`. Secondary: `failure_mode_classified_runtime_health` and `failure_mode_classified_partial_payload`. Slot contention remains `failure_mode_inconclusive` because slot/task-to-document mapping is missing.

## 5. Runtime-Health Behavior

Cell C recorded `23` samples where port `8002` stayed open while `/health` was false. The first was `2026-05-04T05:16:46.483150+00:00` and the last was `2026-05-04T05:28:31.947498+00:00`. `/slots` probes timed out `53` times. GPU evidence did not show a VRAM-critical condition; max observed VRAM used was `16988` MB and min observed free was `7588` MB.

## 6. Timeout Behavior

Cell C recorded `4` llama.cpp request timeouts at about 120 seconds. The client timeout path is the `llm.py` effective timeout passed into `llamacpp_runtime.py` and used by `httpx` for `/v1/models` and `/v1/chat/completions`. No server-timeout tuning is recommended, and increasing the timeout is not a correctness guardrail.

## 7. Partial Payload Leakage

Yes. Failed per-table LLM calls in multipass Pass 3a can be caught, retried with truncated input, omitted if still failing, and the remaining payload can continue into real-gold scoring. The trust layer then reacts to missing/wrong/context outcomes; it does not know that the runtime was unhealthy or that a request timed out. QBE missed `net_debt` and trust abstained in Cell C.

## 8. Recommended Guardrail

Diagnostic guardrail: fail fast or quarantine a cell on either condition: active runtime sample has `port_open=true` and `health_ok=false`, or any captured `llm_request_timings.error` matches timeout markers such as `timeout`, `timed out`, or `deadline exceeded`. A failed guard must invalidate timing comparison and block promotion.

## 9. Files Changed

- `scripts/run_docling_parallel2_experiment.py`: harness gate now classifies per-request LLM timeout rows.
- `scripts/test_run_docling_parallel2_experiment.py`: focused tests for timeout classification.
- `reports/docling_runtime_parallel2_health_audit_20260504T055357Z/`: audit artifacts.

## 10. Tests Run

`financial-engine_v2/.venv/bin/python -m pytest scripts/test_run_docling_parallel2_experiment.py scripts/test_run_isolated_docling_control.py -q` -> 12 passed.

## 11. Artifacts Produced

- `health_audit_summary.md`
- `failure_taxonomy.md`
- `request_timeout_analysis.md`
- `runtime_health_timeline.csv`
- `slot_mapping_notes.md`
- `correctness_gate.json`
- `commands_run.txt`
- `DATA_MISSING.md`

## 12. DATA_MISSING

See `DATA_MISSING.md`. The main missing evidence is slot/task-to-document mapping, typed timeout reason fields, and a source-harness active health timeline for non-diagnostic experiment runs.

## 13. Next Safe Step

Add diagnostic-only active health fail-fast instrumentation to the source experiment harness before any future parallel2 candidate run. Do not promote concurrent document extraction until request-timeout and runtime-health gates both remain clean on the selected documents and then on the canonical set.
