
# DATA_MISSING

- No stable mapping from llama.cpp slot/task IDs to document IDs or `llm_request_timings.call_index` values was captured.
- `/health=false` while the port was open identifies runtime instability, but the artifact does not expose the internal llama.cpp root cause.
- Timeout reason is captured as string text in request errors, not as a typed field such as `timeout_kind=client_read_timeout`.
- The artifact-local diagnostic driver captured `request_health_timeline.csv`; the source experiment harness did not yet capture an active runtime-health timeline for ordinary candidate runs.
- No direct server-side timeout configuration was identified in the inspected Python client path.
- The selected replay did not prove cross-document LLM request interval overlap for the failed calls; slot contention remains inconclusive.
