# Review

## Self Review

- Scope remains inside the task-card allowlist.
- Route guard implementation is narrow: four backend read routes now declare
  `Depends(require_api_key)`.
- Tests assert missing/wrong keys reject before memory work executes, matching
  keys succeed, and empty local key preserves local-dev behavior.
- The PR #439 review finding is satisfied by current canonical code:
  `BackendApiClient.get_company_dump()` sends `_api_key_headers()` and
  `test_backend_api_client_context.py` asserts the header.
- The older context-diagnostics test expectation for unauthenticated
  company-dump redaction is superseded by the memory-read guard: company-dump
  now fails closed with `401`, while ticker context continues to redact.
- No durable memory stores are touched by validation.

## Open Risk

Runtime/browser behavior is not proven until a live backend or browser smoke is
run with configured API keys.
