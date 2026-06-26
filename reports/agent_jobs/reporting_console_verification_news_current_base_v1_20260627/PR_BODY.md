## Summary

Supersedes conflicting PR #133 with a current-base replacement for three small
Cockpit Reporting issues:

- Fixes #45 by gating Vercel Analytics behind `VERCEL=1` or
  `NEXT_PUBLIC_ENABLE_VERCEL_ANALYTICS=1`, so local Cockpit runtime does not
  request `/_vercel/insights/script.js` by default.
- Fixes #47 by keeping the Verification review Recent runs and Saved review
  sessions Select controls controlled with stable sentinel values.
- Fixes #49 by mapping the News page Lookback selector to the existing
  `/rag/query` `date_from` contract for `source="news"`.

## Safety

- Base: `migration/clean-runtime-baseline-reconstruct-v1`
- Supersedes PR #133's patch path only; PR #133 is left open/visible.
- No backend API, RAG ranking, storage, financial truth, memory, source-label,
  production data, runtime service, GPU, or LLM configuration changes.

## Validation

- `tenn-git-guard` portable preflight: pass
- task-card validate: pass
- registry list/check-overlap/claim: pass
- ledger validate: pass
- `git diff --check`: pass
- task-card `check-diff`: pass

Local frontend validation is `DATA_MISSING`: this fresh worktree has no
`cockpit-ui/node_modules`, and `vitest` / `eslint` commands are unavailable. No
dependency install was run. Keeping this PR draft until GitHub CI passes.

The first local push attempt was also blocked by missing local hook tools
(`financial-engine_v2/.venv/bin/ruff` and `financial-engine_v2/.venv/bin/pytest`).
The branch was pushed only with the documented missing-hook bypass and remains
draft pending CI.

## Evidence

- Task card:
  `docs/agent_tasks/reporting_console_verification_news_current_base_v1_20260627.md`
- Report:
  `reports/agent_jobs/reporting_console_verification_news_current_base_v1_20260627/README.md`

Fixes #45
Fixes #47
Fixes #49
