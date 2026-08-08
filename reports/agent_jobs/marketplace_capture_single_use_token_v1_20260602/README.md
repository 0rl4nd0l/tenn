# Marketplace Capture Single-Use Token

## Summary

GitHub issue #217 was implemented in an isolated Reporting worktree. Marketplace capture helper tokens are now consumed on the first submit attempt before backend ingest relay, so replay with the same token follows the expired-helper 410 path and does not call backend ingest.

## Scope

- Changed `cockpit-ui/lib/marketplace-capture-tokens.ts` from read-only token lookup to single-use token consumption.
- Updated the Marketplace capture submit route to call the consume helper.
- Added focused Vitest coverage for valid-token single use, expired tokens, submit replay, and backend-failure consumption.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/marketplace_capture_single_use_token_v1_20260602.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/marketplace_capture_single_use_token_v1_20260602.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/marketplace_capture_single_use_token_v1_20260602.md`
- `corepack pnpm --dir cockpit-ui install --frozen-lockfile`
- `corepack pnpm --dir cockpit-ui exec vitest run lib/marketplace-capture-tokens.test.ts`
- `corepack pnpm --dir cockpit-ui exec eslint lib/marketplace-capture-tokens.ts lib/marketplace-capture-tokens.test.ts app/api/cockpit/commentary/marketplace-capture/submit/route.ts`
- `corepack pnpm --dir cockpit-ui exec tsc --noEmit --pretty false`
