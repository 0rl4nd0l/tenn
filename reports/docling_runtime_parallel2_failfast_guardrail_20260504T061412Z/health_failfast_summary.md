# Health Fail-Fast Summary

## 1. Lane Classification

Lane: Financial Truth. Mode: AUDIT -> SAFE EXTENSION.

## 2. Collision Assessment

Worktree collision risk is elevated because unrelated files were already modified before this lane. This guardrail changes only the parallel2 experiment harness, its focused tests, and this report directory.

## 3. Execution Mode

Diagnostic-only harness extension. No production extraction path, prompts, gold labels, metric normalization, trust semantics, timeout budgets, routing, fallback behavior, or shared `:8001` extraction use was changed.

## 4. Guardrail Added

Parallel2 candidate gates now invalidate timing comparisons when any of these are observed: captured LLM request timeout, active `port_open=true` with `health_ok=false`, active `/slots` timeout, or a timeout-contaminated partial payload that continues into scoring.

Cell C now captures active request/runtime health samples in the payload and writes `request_health_timeline.csv` when a candidate run produces samples.

## 5. Failure Classes Detected

The harness classifies `failure_mode_classified_request_timeout`, `failure_mode_classified_runtime_health`, `failure_mode_classified_slots_timeout`, and `failure_mode_classified_partial_payload`.

## 6. Partial Payload Scoring

Partial payloads can still enter scoring under existing production extraction semantics after per-table LLM timeouts. This patch does not change that behavior; it makes the diagnostic harness reject the experiment cell when timeout evidence is followed by scoring payload fields.

## 7. Files Changed

- `scripts/run_docling_parallel2_experiment.py`
- `scripts/test_run_docling_parallel2_experiment.py`
- `reports/docling_runtime_parallel2_failfast_guardrail_20260504T061412Z/`

## 8. Tests Run

- `financial-engine_v2/.venv/bin/python -m pytest scripts/test_run_docling_parallel2_experiment.py scripts/test_run_isolated_docling_control.py -q`
- `financial-engine_v2/.venv/bin/python -m ruff check scripts/run_docling_parallel2_experiment.py scripts/test_run_docling_parallel2_experiment.py`
- `git diff --check -- scripts/run_docling_parallel2_experiment.py scripts/test_run_docling_parallel2_experiment.py`

## 9. Artifacts Produced

- `health_failfast_summary.md`
- `correctness_gate.json`
- `commands_run.txt`
- `DATA_MISSING.md`

`request_health_timeline.csv` was not generated in this coding-only validation pass because no live Cell C candidate was executed.

## 10. DATA_MISSING

Slot/task-to-document mapping remains unresolved.

## 11. Next Safe Step

Run a bounded parallel2 candidate only after this guardrail is in place, then accept no timing comparison unless request-timeout, runtime-health, `/slots`, partial-payload, prompt-cache, isolation, cache, trust, context, and metric gates all remain clean.
