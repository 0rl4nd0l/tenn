# Issue #241 Extraction Review Route Guard

## Status

status: DONE_WITH_RISK

DONE_WITH_RISK: current-base fix implemented and backend validation passed.
Frontend API-client validation is blocked locally because `cockpit-ui/node_modules`
and `cockpit-ui/node_modules/.bin/vitest` are absent. No runtime service or live
API smoke was started.

## Scope

- GitHub issue: #241
- Branch: `safe/issue241-extraction-review-route-guard-current-base-v1-20260627`
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1@7d6ab6c184332d5413700eb08e6790f530000942`
- PR: https://github.com/0rl4nd0l/tenn/pull/436
- Task card: `docs/agent_tasks/issue241_extraction_review_route_guard_current_base_v1_20260627.md`
- Old work classification: `ADOPT/PRESERVE`

## Changes

- Added `Depends(require_api_key)` to extraction-review read routes for runs,
  sessions, session contents, errors, run status, and snippet images.
- Added focused backend route-auth regression coverage.
- Updated Cockpit extraction-review API-client reads to send `X-API-Key`.
- Added guarded snippet blob fetching and wired the verification review panel to
  render the protected object URL instead of directly loading the backend route.
- Updated backend API surface docs for the extraction-review auth boundary.

## Runtime Functionality Proof

result: PARTIAL

| Field | Required evidence |
| --- | --- |
| intended output | Extraction-review read routes deny configured-key unauthenticated calls and allow authenticated operator reads/snippet loads. |
| live output location | `/api/extraction-review/runs`, `/sessions`, `/session/{session_id}`, `/errors`, `/run/{run_id}`, `/snippets/{image_name}`. |
| pre-run max timestamp or count | RED focused pytest: 6 missing-key cases returned 200 instead of 401; 8 passed. |
| post-run max timestamp or count | GREEN focused backend suite: 34 passed. Live service count/timestamp: DATA_MISSING. |
| rows/files inserted or updated after run start | Production rows: 0. Repo files changed are restricted to task-card allowlist. |
| readiness/gate status | Local backend tests pass; frontend Vitest blocked by missing local dependencies; PR/CI pending. |
| exact command/query used | See `VALIDATION.md`. |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | PARTIAL. |
| remaining blocker | Local frontend test dependencies absent; no approved live runtime/API smoke. |

## Docs Impact

- `docs_impact`: `DOCS_UPDATED`
- `docs_checked`: `docs/README.md`, `docs/architecture/19_backend_api_surface.md`
- `docs_changed`: `docs/architecture/19_backend_api_surface.md`
- `docs_followup`: none
- `reason`: route auth behavior changed for extraction-review read APIs.

## Unsafe Actions Avoided

- No DB, Qdrant, Redis, source PDF, report data, gold label, parser prompt,
  runtime service, model/GPU config, or production data mutation.
- No dependency install or lockfile/package manifest mutation.
- No merge, rebase, reset, stash, clean, branch deletion, or issue close.

## Next

Wait for PR #436 CI, then close issue #241 only after the PR is merged or owner
explicitly approves issue closeout from PR evidence.
