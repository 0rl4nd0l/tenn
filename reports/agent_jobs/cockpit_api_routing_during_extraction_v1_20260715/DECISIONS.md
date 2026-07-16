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
7. Adopt the owner-approved controlled activation manifest and recreate only
   backend, worker, and GPU worker with `--no-deps` after extraction and queue
   gates are empty.
8. Prove normal and GPU-exclusive routing with stateless requests, zero DB/news
   persistence delta, and llama journal comparison before promotion.
9. Treat the real shared routing-state token as a route-class proof, not as a
   claim that a real extraction was started; starting extraction remained
   forbidden.
10. Proceed with push, PR, and merge after full Git guard, exact-head review,
    required checks, and the review-board decision remain green.
11. Keep the pre-existing UI outage outside this merge and route it to a
    separate read-only diagnosis and restoration manifest.
12. Repair PR #512's stale attached-source assertion by reading HybridRouter's
    `prompt` keyword argument; do not change production routing behavior.
