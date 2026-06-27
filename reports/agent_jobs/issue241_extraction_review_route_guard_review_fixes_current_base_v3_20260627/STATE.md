# State

## Verified

- Worktree:
  `/home/l4nd0/tenn-issue241-extraction-review-route-guard-review-fixes-current-base-v3-20260627`
- Branch:
  `safe/issue241-extraction-review-route-guard-review-fixes-current-base-v3-20260627`
- Base/head:
  `968a613b24783e1929a893ff1f098d8ff63a8ef5`
- Guard classification:
  `VALID_TASK_WORKTREE`
- Old PR #451:
  `OPEN`, `DIRTY`, `CONFLICTING`, checks previously green on stale head
  `c7e88d0f928ce18b6db335760beb1ec6f559a1a3`

## Changes

- Added `Depends(require_api_key)` to extraction-review read routes:
  `/runs`, `/sessions`, `/session/{session_id}`, `/errors`, `/run/{run_id}`,
  and `/snippets/{image_name}`.
- Added focused backend route-auth tests, including snippet auth and traversal
  guard coverage.
- Updated Cockpit API-client extraction-review reads and snippet blob fetches
  to send configured API-key headers.
- Updated verification UI image rendering to consume object URLs returned by
  the authenticated fetch helper.
- Updated Python/Textual `BackendApiClient` review reads to send API-key
  headers.
- Updated API-surface docs while preserving Intel Pulse and TradingView auth
  documentation from already-merged PRs.

## Functionality Result

`PARTIAL`: route/client code is locally validated, but live runtime output was
not checked. No DB, source PDFs, extraction outputs, snippets, services, or
runtime configuration were mutated.

## Runtime Functionality Proof

| Field | Required evidence |
| --- | --- |
| intended output | Guarded extraction-review HTTP read routes and snippet image fetches require/forward API-key credentials when `settings.local_api_key` is configured. |
| live output location | `DATA_MISSING`: no live backend/API/browser surface was started or queried in this task. Code surfaces checked: `financial-engine_v2/backend/app/api/extraction_review.py`, `cockpit-ui/lib/api-client.ts`, and `financial-engine_v2/cockpit/integrations/backend_api.py`. |
| pre-run max timestamp or count | `DATA_MISSING`: no live route/session/snippet baseline captured. |
| post-run max timestamp or count | `DATA_MISSING`: no live route/session/snippet post-run check captured. |
| rows/files inserted or updated after run start | 0 runtime rows/files; only repo files and report artifacts were changed. |
| readiness/gate status | Local code gate partial: backend pytest 55 passed, ruff passed, py_compile passed, diff checks passed; frontend Vitest blocked because `vitest` is not installed; live runtime gate `DATA_MISSING`. |
| exact command/query used | Local validation commands are listed in `VALIDATION.md`; no live HTTP/API/browser command was run. |
| result | PARTIAL |
| remaining blocker | Live backend/browser smoke and frontend Vitest require available runtime/tooling and are not proven in this task. |

result: PARTIAL
