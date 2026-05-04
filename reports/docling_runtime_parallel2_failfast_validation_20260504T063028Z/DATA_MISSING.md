# DATA_MISSING

- Slot/task-to-document mapping remains unresolved.
- No active request-health samples exist for this run because `:8002` failed before document extraction began.
- No concurrency timeline exists because no Cell C child extraction processes reached LLM request execution.
- Correctness, trust, and context gates were not evaluated because Cell A was blocked by VRAM/runtime startup failure.
- Runtime-level prompt-cache controls could not be sampled because the dedicated extraction runtime did not become healthy.
