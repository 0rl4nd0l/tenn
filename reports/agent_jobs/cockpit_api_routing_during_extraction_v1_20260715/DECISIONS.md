# Decisions

1. Keep `multipass_extraction` pinned to the existing deterministic local
   instruct route.
2. Build Cockpit's HybridRouter in both keyword and structured modes so legacy
   keyword synthesis cannot bypass GPU ownership or API policy.
3. While extraction activity is registered, route every non-metric
   `generate_json` call to Anthropic before local route selection.
4. Fail fast if Anthropic is unavailable during extraction instead of
   contending for the protected local llama.cpp router.
5. Record effective provider, model, endpoint, and routing reason in mutable
   call metadata and news memo provenance.
6. Replace retired `claude-sonnet-4-20250514` defaults with Anthropic's
   canonical `claude-sonnet-4-6`; retain historical pricing lookup coverage.
7. Stop before live activation because service restart and runtime mutation
   were outside the approved code-only lane.
