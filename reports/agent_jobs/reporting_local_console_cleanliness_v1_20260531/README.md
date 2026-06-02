# Reporting local console cleanliness v1

## Scope

Remediated GitHub issues #45 and #47 in an isolated Reporting worktree.

## Changes

- `cockpit-ui/app/layout.tsx` gates Vercel Analytics behind `VERCEL=1` or `NEXT_PUBLIC_ENABLE_VERCEL_ANALYTICS=1`, so local Cockpit runtime does not render the Vercel analytics script by default.
- `cockpit-ui/components/cockpit/verification/tabs/review-tab-panel.tsx` uses stable sentinel values for optional Recent runs and Saved review sessions Select controls.
- `cockpit-ui/components/cockpit/verification/tabs/review-tab-panel.test.tsx` covers the controlled-selector transition.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/reporting_local_console_cleanliness_v1_20260531.md` passed.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/reporting_local_console_cleanliness_v1_20260531.md` passed.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/reporting_local_console_cleanliness_v1_20260531.md` passed.
- `corepack pnpm --dir cockpit-ui install --frozen-lockfile` completed from the existing lockfile.
- `corepack pnpm --dir cockpit-ui exec vitest run components/cockpit/verification/tabs/review-tab-panel.test.tsx components/cockpit/news/news-screen.test.tsx` passed: 2 files, 3 tests.
- `corepack pnpm --dir cockpit-ui exec eslint app/layout.tsx components/cockpit/verification/tabs/review-tab-panel.tsx components/cockpit/verification/tabs/review-tab-panel.test.tsx` passed.
- `corepack pnpm --dir cockpit-ui exec tsc --noEmit` passed.
- `corepack pnpm --dir cockpit-ui exec next build` passed.
- Temporary `next start` on `127.0.0.1:3107` returned home HTML without `_vercel/insights/script.js` or `Vercel Web Analytics`.
- `git diff --check` passed.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/reporting_local_console_cleanliness_v1_20260531.md` passed.

## Boundaries

No backend API, RAG, financial truth, memory, source-label, production data, runtime service, GPU, or LLM configuration changes were made.
