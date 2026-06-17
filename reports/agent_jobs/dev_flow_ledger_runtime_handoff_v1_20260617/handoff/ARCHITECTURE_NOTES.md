# Architecture Notes

The selected implementation is intentionally small:

- one standard-library runtime script
- one focused test file
- one repo-native handoff skill
- narrow edits to existing Tenn dev-flow skills
- docs/templates only for ledger and handoff shape

Avoided layers:

- scheduler or daemon
- DB/service dependency
- host-global skill mutation
- product/runtime/data/extraction imports or behavior

Residual concern: live ledger append mutates shared registry state outside git,
so this task preserves the current entry report-locally and leaves live append
for a future explicitly approved workflow.
