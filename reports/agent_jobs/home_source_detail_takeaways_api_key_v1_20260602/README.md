# Home Source Detail Takeaways API Key

## Summary

GitHub issue #231 was implemented in an isolated Reporting worktree. Cockpit Home now sends the configured Cockpit API key on the main Home BFF request and on source-detail takeaways requests when a key is available.

## Scope

- Added Home client key loading from `localStorage['cockpit.apiKey']` with `NEXT_PUBLIC_API_KEY` fallback.
- Added `X-API-Key` to `GET /api/cockpit/home` browser requests when configured.
- Passed the configured key into the Home source-detail drawer.
- Added `X-API-Key` to source-detail `POST /api/cockpit/commentary/takeaways` requests while preserving the existing `source_id` and `limit` body.
- Added focused Home tests for both request paths.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/home_source_detail_takeaways_api_key_v1_20260602.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/home_source_detail_takeaways_api_key_v1_20260602.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/home_source_detail_takeaways_api_key_v1_20260602.md`
- `corepack pnpm --dir cockpit-ui install --frozen-lockfile`
- `corepack pnpm --dir cockpit-ui exec vitest run lib/cockpit-home-api.test.ts`
- `corepack pnpm --dir cockpit-ui exec eslint components/cockpit/home/home-page.tsx components/cockpit/home/source-detail-drawer.tsx lib/cockpit-home-api.test.ts`
- `corepack pnpm --dir cockpit-ui exec tsc --noEmit --pretty false`
- `git diff --check`
