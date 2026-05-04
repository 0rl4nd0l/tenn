# DATA_MISSING

- Slot/task-to-document mapping remains unresolved. The harness can correlate client request intervals and document ids, but llama.cpp `/slots` task ids are not joined to harness document ids.
- No live `request_health_timeline.csv` was generated in this coding-only validation pass. The harness now writes that CSV when a parallel2 candidate run records request-health samples.
