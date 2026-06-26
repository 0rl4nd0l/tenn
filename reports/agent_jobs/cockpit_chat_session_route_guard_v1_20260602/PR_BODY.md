## Summary

- Require the configured local API key for direct backend Cockpit chat/session routes.
- Forward the configured browser API key for chat session CRUD, blocking chat, and SSE chat.
- Add focused backend red/green coverage and API-client tests for the forwarding path.

## Validation

- Backend RED on current base with test-only patch: `16 failed, 89 passed`
- Backend GREEN: `105 passed, 5 warnings`
- Ruff: passed
- `python3 -m py_compile`: passed
- `git diff --check`: passed
- Task-card validation: passed
- Ledger validation: passed

Frontend local validation is `DATA_MISSING`: `npm test -- --run lib/api-client.test.ts` exited 127 because `vitest` is not installed in this checkout.

Refs #229
