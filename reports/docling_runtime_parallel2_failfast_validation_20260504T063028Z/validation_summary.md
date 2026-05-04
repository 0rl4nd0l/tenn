# Parallel2 Fail-Fast Validation

Overall verdict: `blocked_vram_preflight`.

## 1. Lane Classification

Lane: Financial Truth. Mode: AUDIT -> SAFE EXTENSION.

## 2. Collision Assessment

Collision risk is elevated. The worktree already contained unrelated modified and untracked files before this lane. This lane touched only the parallel2 diagnostic harness, its focused tests, and this report directory.

## 3. Execution Mode

Bounded selected-doc replay was attempted only for:

- `bhp_a_2025-06-30`
- `qbe_h_2025-06-30`
- `rio_a_2023-12-31`
- `eqr_q_2025-12-31`

## 4. Guardrail Behavior Observed

The fail-fast Cell C guardrail was not reached. Cell A could not start the dedicated extraction runtime because `:8002` failed during model load with CUDA out-of-memory evidence in `llama_extraction_8002_parallel1.log`.

## 5. Actual Concurrent LLM Requests

No. The run did not create concurrent LLM requests because `:8002` never became healthy.

## 6. Correctness / Trust / Context

Not evaluated. Cell A, B, and C document extraction did not run.

## 7. Runtime Provenance

Dedicated extraction runtime target: `http://127.0.0.1:8002`.

Shared runtime `http://127.0.0.1:8001` was not used for extraction. It was observed as the resident authorized chat/router process.

## 8. Prompt Cache Status

Prompt cache was requested disabled with `LLAMA_ARG_CACHE_RAM=0`, `LLAMA_ARG_CACHE_PROMPT=false`, and `--disable-prompt-cache`. Runtime-level confirmation is unavailable because `:8002` failed before becoming healthy.

## 9. Health / Timeout / Slots Timeline

No `request_health_timeline.csv` was generated because no active extraction request samples existed. The attempted `:8002` runtime stayed unavailable and ended before any Cell C health sampling.

## 10. Timing Comparison

Rejected. No timing comparison is accepted because the runtime/VRAM preflight failed before the selected-doc replay could start.

## 11. Files Changed

- `scripts/run_docling_parallel2_experiment.py`
- `scripts/test_run_docling_parallel2_experiment.py`
- `reports/docling_runtime_parallel2_failfast_validation_20260504T063028Z/`

## 12. Tests Run

- `financial-engine_v2/.venv/bin/python -m pytest scripts/test_run_docling_parallel2_experiment.py scripts/test_run_isolated_docling_control.py -q` (`20 passed`)
- `financial-engine_v2/.venv/bin/python -m ruff check scripts/run_docling_parallel2_experiment.py scripts/test_run_docling_parallel2_experiment.py`
- `git diff --check -- scripts/run_docling_parallel2_experiment.py scripts/test_run_docling_parallel2_experiment.py`
- `jq empty` on validation JSON artifacts

## 13. Artifacts Produced

- `validation_summary.md`
- `correctness_gate.json`
- `runtime_provenance.json`
- `prompt_cache_provenance.json`
- `gpu_preflight.json`
- `per_doc_timing.csv`
- `per_stage_timing.csv`
- `performance_matrix.json`
- `commands_run.txt`
- `DATA_MISSING.md`
- `llama_extraction_8002_parallel1.log`

## 14. DATA_MISSING

Slot/task-to-document mapping remains unresolved. No active request-health samples, concurrency intervals, or correctness rows exist for this blocked run.

## 15. Next Safe Step

Rerun the same selected-doc replay only after enough VRAM is available for the dedicated `:8002` extraction model without changing extraction semantics, prompts, gold labels, trust rules, prompt-cache behavior, routing, fallback behavior, or timeout budgets.
