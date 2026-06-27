# State

- Branch: `safe/issue241-extraction-review-route-guard-review-fixes-current-base-v2-20260627`
- Base: `origin/migration/clean-runtime-baseline-reconstruct-v1`
- Base HEAD: `eb4a42910fd71077af4a389bd4a9f4400796921b`
- Issue: #241
- Supersedes: PR #436 by replacement branch only.
- Existing PR #436 state at scouting: open, `DIRTY` / `CONFLICTING`, stale
  checks green, one P2 review finding about snippet image refetches.

## Safety

- No production/runtime data mutation.
- No services started.
- No dependency installation.
- No stale branch/worktree mutation.

## Changes

- Added `require_api_key` dependencies to extraction-review read routes:
  `/runs`, `/sessions`, `/session/{session_id}`, `/errors`, `/run/{run_id}`,
  and `/snippets/{image_name}`.
- Updated Cockpit extraction-review read helpers to send `X-API-Key`.
- Added an authenticated snippet blob fetch helper and wired Verification UI to
  render blob URLs instead of raw guarded route URLs.
- Stabilized the review-session refresh callback passed to `useSnippetImage` to
  avoid the PR #436 repeated-refetch loop.
- Added focused backend and API-client regressions.
- Updated backend API-surface docs.
