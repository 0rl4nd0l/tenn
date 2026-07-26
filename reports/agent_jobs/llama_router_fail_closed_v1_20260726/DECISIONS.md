# Decisions

- Preserve the exact configured binary, models, presets, request shape, and
  runtime state.
- When router mode is explicitly requested, capability uncertainty is fatal;
  never reinterpret it as permission to serve the single-model fallback.
- Add a regression that proves the launcher exits before invoking the serving
  command when the router capability is absent.
- Document that router capability uncertainty is fatal and that operators must
  choose `LLAMA_SERVER_ROUTER_MODE=0` explicitly for single-model startup.
- No subagent delegation: the source and test changes are tightly coupled and
  fit one bounded milestone.
