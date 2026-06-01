# Cockpit Accessible Controls: News and History

Status: ready for review

## Scope

This slice addresses a narrow part of GitHub issue #53:

- News search query, ticker filter, and lookback controls now have durable accessible names.
- History job expand/collapse controls now expose action-specific accessible names.
- History details column now exposes a non-empty accessible header.

This does not close #53. The issue remains open for the broader route-level accessibility sweep.

## Boundaries

No backend, retrieval, storage, parser, source-label, memory, financial truth, or runtime behavior was changed. The change is limited to Cockpit UI Reporting files and focused component tests.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_accessible_controls_news_history_v1_20260602.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_accessible_controls_news_history_v1_20260602.md`
- `./node_modules/.bin/vitest run components/cockpit/news/news-screen.test.tsx components/cockpit/history/history-screen.test.tsx`
- `./node_modules/.bin/eslint components/cockpit/news/news-screen.tsx components/cockpit/news/news-screen.test.tsx components/cockpit/history/history-screen.tsx components/cockpit/history/history-screen.test.tsx`
- `./node_modules/.bin/tsc --noEmit`
- `git diff --check`

The isolated worktree temporarily symlinked `cockpit-ui/node_modules` to the shared checkout's dependency directory for local validation because `pnpm` was not available on `PATH` and the sibling worktree had no local `node_modules`. The symlink was removed before staging.
