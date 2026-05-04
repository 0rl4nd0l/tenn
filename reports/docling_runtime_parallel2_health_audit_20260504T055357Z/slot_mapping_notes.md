
# Slot Mapping Notes

The artifact includes `/slots` probe status/snapshot fields in `request_health_timeline.csv`; the derived timeline is `runtime_health_timeline.csv`. It does not include a stable mapping from llama.cpp slot/task IDs to harness document IDs or LLM `call_index` values.

Available evidence:

- `/slots` probe timeout samples: `53`.
- Port-open/health-false samples: `23`.
- Captured request-level timeout documents: `bhp_a_2025-06-30`, `qbe_h_2025-06-30`, `rio_a_2023-12-31`.
- Selected replay `concurrency_timeline.csv` did not prove cross-document LLM interval overlap for the failed request rows, although the cell was launched with two concurrent document clients and prior Cell C evidence remains part of the diagnostic package.

Conclusion: slot contention is plausible but not classified. The next safe instrumentation step is to capture slot/task ID, request start/end, document ID, and LLM call index in one timeline.
