# Review

## Scope Review

Touched files are limited to the task-card allowlist:

- Cockpit runtime-topology backend routes and tests.
- Cockpit API-client helpers/tests and direct config fetch callers.
- Backend API surface documentation.
- Task-card and report artifacts.

## Risk Review

- The backend guard uses the existing `require_api_key` dependency, so no new
  auth mechanism is introduced.
- Existing no-key local development behavior is preserved by
  `require_api_key`.
- Direct config fetch callers now send the stored or env API key where the
  helper API path could not be used.
- The UI test could not be run locally because the local checkout lacks
  `vitest`; GitHub checks are required before merge.
- Local code review found one env-only API-key forwarding gap in
  `chat-screen.tsx`; it was fixed by switching that direct config fetch to
  `withApiKey()`.
- Codex PR review found one P2: `scripts/cockpit_routing_smoke.py` could not
  authenticate the newly guarded config read. It was fixed by adding API-key
  CLI/env plumbing and focused smoke-script tests.

## Residual Risk

Runtime/browser functionality is not proven. The route-level behavior is covered
by focused backend tests, but no live backend or browser smoke was run.
