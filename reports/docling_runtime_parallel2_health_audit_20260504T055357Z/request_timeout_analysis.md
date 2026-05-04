
# Request Timeout Analysis

## Summary

Cell C contains `4` captured llama.cpp request timeouts at about 120 seconds. These are request-level failures inside `llm_request_timings`, not necessarily document-level `extraction_error` values. The prior gate therefore reported `no_timeout: true` even though the raw request timeline contained timeouts.

## Timeout Inventory

| Document | Call | Elapsed seconds | Prompt chars | Error |
| --- | ---: | ---: | ---: | --- |
| `bhp_a_2025-06-30` | 4 | 120.258 | 6748 | `llama.cpp JSON generation failed at http://127.0.0.1:8002/v1/chat/completions: timed out` |
| `rio_a_2023-12-31` | 3 | 120.303 | 6892 | `llama.cpp JSON generation failed at http://127.0.0.1:8002/v1/chat/completions: timed out` |
| `qbe_h_2025-06-30` | 2 | 120.248 | 7028 | `llama.cpp JSON generation failed at http://127.0.0.1:8002/v1/chat/completions: timed out` |
| `qbe_h_2025-06-30` | 4 | 120.247 | 6486 | `llama.cpp JSON generation failed at http://127.0.0.1:8002/v1/chat/completions: timed out` |


## Client Timeout

`financial-engine_v2/backend/app/services/llm.py` resolves the effective llama.cpp timeout from the call argument or `settings.llamacpp_timeout_seconds`. Multipass extraction does not pass a special timeout, so the default 120-second request timeout applies. `financial-engine_v2/backend/app/services/llamacpp_runtime.py` uses that timeout for both `/v1/models` and `/v1/chat/completions` through `httpx.Client(timeout=timeout)`.

## Server Timeout

No separate llama.cpp server-side request timeout was identified in the inspected Python client path. The server log contains task-cancel and `/slots` probe timeout evidence, but the current artifact does not map server slot/task IDs back to document IDs.

## Subprocess Timeout

The diagnostic child/cell subprocess timeouts are much larger than the failed request durations and are not the observed trigger. The failures happened inside HTTP requests around the 120-second client boundary.

## Retry and Backoff

Pass 3a catches a failed per-table LLM call, logs it, retries with a truncated table prompt, and can return `None` if the retry also fails. There is no backoff strategy for these per-table failures. Production fallback remains disabled for multipass extraction.

## Harness Fix Applied

`_cell_gate()` in `scripts/run_docling_parallel2_experiment.py` now checks captured `llm_request_timings` errors for timeout markers. The gate fails if request-level timeouts are present even when the prior document-level acceptance flag did not see `timeout_event`.
