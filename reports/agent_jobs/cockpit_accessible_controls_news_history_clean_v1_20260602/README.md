# Cockpit Accessible Controls: News/History Clean Replacement

Issue: #53

Supersedes wrong-base slice: PR #208

Branch: `safe/cockpit-accessible-controls-news-history-clean-v1-20260602`

Worktree:
`/home/l4nd0/tenn-cockpit-accessible-controls-news-history-clean-v1-20260602`

## Outcome

Implemented a clean, UI-only accessible-name remediation for the News and
History slice from `origin/migration/clean-runtime-baseline-reconstruct-v1`.
News search, ticker filter, and lookback controls now have durable programmatic
names. History job expand/collapse icon buttons now expose action-specific
names, and the details column has a screen-reader-visible header.

This is a partial remediation slice for #53, not a full issue closeout. Other
route-level accessible-control inventory remains open or covered by separate
PRs.

## Why This Replacement Exists

PR #208 contains the intended News/History UI behavior, but current live PR
evidence shows it targets `audit/issue98-current-branch-status-v1-20260602`
instead of `migration/clean-runtime-baseline-reconstruct-v1`. This branch
recreates only the UI slice on the correct baseline.

## Boundaries

- No backend, extraction, retrieval, memory, Qdrant/Postgres, financial truth,
  source/evidence label, runtime/model/GPU, or service config changes.
- No broad UI redesign.
- No route closure claim for #53.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_accessible_controls_news_history_clean_v1_20260602.md --write-report` passed.
- `python3 scripts/agent_job_registry.py list-active` passed with no active jobs before claim.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_accessible_controls_news_history_clean_v1_20260602.md --repo-root .` passed.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_accessible_controls_news_history_clean_v1_20260602.md --repo-root .` passed.
- `corepack pnpm --dir cockpit-ui install --frozen-lockfile` completed from the lockfile.
- `corepack pnpm --dir cockpit-ui exec vitest run components/cockpit/news/news-screen.test.tsx components/cockpit/history/history-screen.test.tsx` passed: 2 files, 4 tests.
- `corepack pnpm --dir cockpit-ui exec eslint components/cockpit/news/news-screen.tsx components/cockpit/news/news-screen.test.tsx components/cockpit/history/history-screen.tsx components/cockpit/history/history-screen.test.tsx` passed.
- `corepack pnpm --dir cockpit-ui exec tsc --noEmit --pretty false` passed.
- `python3 -m json.tool` passed for the report JSON files.
- Code-reviewer pass found no blocking findings.
- `git diff --check && git diff --cached --check` passed.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_accessible_controls_news_history_clean_v1_20260602.md --repo-root .` passed.
- `python3 scripts/agent_job_registry.py release cockpit_accessible_controls_news_history_clean_v1_20260602` passed.
- Final `python3 scripts/agent_job_registry.py list-active` passed with no active jobs.

## DATA_MISSING

- Full #53 route-wide completion remains unproven; this report only covers the
  News/History slice.
