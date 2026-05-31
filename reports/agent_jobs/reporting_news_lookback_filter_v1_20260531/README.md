# Reporting News lookback filter v1

## Scope

Remediated GitHub issue #49 in the existing Reporting draft PR branch.

## Current evidence

- `financial-engine_v2/backend/app/main.py` defines `RagQueryRequest.date_from` and `date_to`.
- `POST /rag/query` passes `date_from` and `date_to` through for `source="news"`.
- `financial-engine_v2/backend/app/services/rag.py` applies `date_from` and `date_to` to the `published_at` Qdrant payload filter.

## Changes

- `cockpit-ui/components/cockpit/news/news-screen.tsx` now translates the selected Lookback value to `date_from` before calling `/rag/query`.
- `cockpit-ui/components/cockpit/news/news-screen.test.tsx` covers lookback date translation and verifies the search payload includes `date_from`.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/reporting_news_lookback_filter_v1_20260531.md` passed.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/reporting_news_lookback_filter_v1_20260531.md` passed.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/reporting_news_lookback_filter_v1_20260531.md` passed.
- `corepack pnpm --dir cockpit-ui exec vitest run components/cockpit/news/news-screen.test.tsx` passed: 1 file, 4 tests.
- `corepack pnpm --dir cockpit-ui exec vitest run components/cockpit/news/news-screen.test.tsx components/cockpit/verification/tabs/review-tab-panel.test.tsx` passed: 2 files, 5 tests.
- `corepack pnpm --dir cockpit-ui exec eslint components/cockpit/news/news-screen.tsx components/cockpit/news/news-screen.test.tsx app/layout.tsx components/cockpit/verification/tabs/review-tab-panel.tsx components/cockpit/verification/tabs/review-tab-panel.test.tsx` passed.
- `corepack pnpm --dir cockpit-ui exec tsc --noEmit` passed.
- `corepack pnpm --dir cockpit-ui exec next build` passed.
- `git diff --check` passed.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/reporting_news_lookback_filter_v1_20260531.md` passed.

## Boundaries

No backend API, RAG ranking, storage, source-label, financial truth, memory, production data, runtime service, GPU, or LLM configuration changes were made.
