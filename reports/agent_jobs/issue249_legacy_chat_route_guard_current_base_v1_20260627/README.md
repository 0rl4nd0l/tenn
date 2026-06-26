# Issue #249 Legacy Chat Route Guard

Status: DONE_WITH_RISK

## Summary

This task guards the legacy backend chat endpoint mounted at both `POST /chat`
and `POST /api/chat` with the existing local API-key dependency.

The change is intentionally narrow:

- `app.routes.chat` now declares `Depends(require_api_key)` on `POST /chat`.
- Because `chat_router` is mounted twice, the guard applies to both `/chat` and
  `/api/chat`.
- Focused tests prove missing or wrong keys are rejected before analysis-mode
  `chat_with_tenn()` or session persistence can run.
- Focused tests prove missing or wrong keys are rejected before strategy-mode
  proposal, confirm, or apply helpers can run.
- Authenticated analysis and strategy behavior is preserved.
- The backend API surface doc now records the guarded legacy chat contract.

## Scope Boundaries

No DB, Qdrant, Redis, news store, memory store, source PDF, extraction output,
prompt, gold label, runtime/model/GPU/service config, or production data was
mutated.

This does not remove, deprecate, or redesign `/chat` or `/api/chat`; legacy
route ownership remains separate under #150/#171. This also does not claim to
fix Cockpit `/api/cockpit/chat` or session-route auth under #229.

## Result

Issue #249 code remediation is complete in this worktree and ready for PR. Live
backend service functionality was not started or proven, so closeout uses
`DONE_WITH_RISK` rather than a live-runtime `DONE`.
