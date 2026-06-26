---
job_id: reporting_console_verification_news_current_base_v1_20260627
lane: Reporting
supporting_lanes:
  - Evaluation
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/reporting_console_verification_news_current_base_v1_20260627
mutation_mode: safe_extension
production_data_access: false
issues:
  - 45
  - 47
  - 49
allowed_files:
  - docs/agent_tasks/reporting_console_verification_news_current_base_v1_20260627.md
  - cockpit-ui/app/layout.tsx
  - cockpit-ui/components/cockpit/verification/tabs/review-tab-panel.tsx
  - cockpit-ui/components/cockpit/verification/tabs/review-tab-panel.test.tsx
  - cockpit-ui/components/cockpit/news/news-screen.tsx
  - cockpit-ui/components/cockpit/news/news-screen.test.tsx
  - reports/agent_jobs/reporting_console_verification_news_current_base_v1_20260627/README.md
  - reports/agent_jobs/reporting_console_verification_news_current_base_v1_20260627/STATE.md
  - reports/agent_jobs/reporting_console_verification_news_current_base_v1_20260627/VALIDATION.md
  - reports/agent_jobs/reporting_console_verification_news_current_base_v1_20260627/REVIEW.md
  - reports/agent_jobs/reporting_console_verification_news_current_base_v1_20260627/PR_BODY.md
  - reports/agent_jobs/reporting_console_verification_news_current_base_v1_20260627/status.json
  - reports/agent_jobs/reporting_console_verification_news_current_base_v1_20260627/diff-check.json
  - reports/agent_jobs/reporting_console_verification_news_current_base_v1_20260627/registry_claim.json
  - reports/agent_jobs/reporting_console_verification_news_current_base_v1_20260627/registry_release.json
  - reports/agent_jobs/reporting_console_verification_news_current_base_v1_20260627/ledger_claimed.json
  - reports/agent_jobs/reporting_console_verification_news_current_base_v1_20260627/ledger_pr_opened.json
github_writes_allowed:
  - push branch after static and contract validation when local frontend dependencies are unavailable
  - open draft PR after static and contract validation when local frontend dependencies are unavailable
  - set TENN_ALLOW_MISSING_HOOK_TOOLS=1 for push only when missing local hook tools are recorded and PR remains draft
  - issue close only after canonical merge containment
---

# Reporting Console, Verification, And News Current-Base Replacement

## Objective

Supersede conflicting PR #133 with a current-base replacement that resolves
issues #45, #47, and #49 without widening into backend, runtime, RAG ranking,
storage, memory, financial truth, or production data behavior.

## Scope

- Gate Vercel Analytics so local Cockpit production runtime does not request
  `/_vercel/insights/script.js` unless Vercel or an explicit public env flag is
  enabled.
- Keep optional Verification review Select controls controlled with sentinel
  values across empty and selected states.
- Wire the News lookback selector into the existing `/rag/query` `date_from`
  request field for `source: "news"`.
- Add focused Cockpit UI regression coverage for the Verification and News
  behavior.
- Record validation and PR closeout evidence under this report bundle.

## Hard Boundaries

- No backend API, RAG ranking, storage, financial truth, memory, source-label,
  production data, runtime service, GPU, or model configuration changes.
- No route contract changes beyond passing the existing `date_from` field in
  the frontend request payload.
- No live service starts unless used only for optional UI verification after
  focused tests pass.
- No merge, rebase, reset, stash, branch deletion, cleanup, or old-PR closure.
- Do not close #45, #47, or #49 before the replacement PR is merged and
  canonical containment is verified.

## Prior Work

PR #133 contains the earlier validated fix but is now merge-conflicting against
`migration/clean-runtime-baseline-reconstruct-v1`. This task ports only the
small source and test changes onto current canonical HEAD and leaves PR #133
visible as superseded evidence.

## Required Validation

- Portable `tenn-git-guard` preflight for this worktree.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/reporting_console_verification_news_current_base_v1_20260627.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/reporting_console_verification_news_current_base_v1_20260627.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/reporting_console_verification_news_current_base_v1_20260627.md --repo-root .`
- Focused Vitest coverage for `components/cockpit/verification/tabs/review-tab-panel.test.tsx` and `components/cockpit/news/news-screen.test.tsx`.
- Targeted ESLint for changed Cockpit UI files.
- `corepack pnpm --dir cockpit-ui exec tsc --noEmit`
- If local `cockpit-ui/node_modules` is absent, record Vitest/ESLint/TypeScript
  as `DATA_MISSING` and keep any PR draft until GitHub CI passes.
- If the pre-push hook reports missing local hook tools, record the blocker and
  only bypass with `TENN_ALLOW_MISSING_HOOK_TOOLS=1` for a draft PR path.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/reporting_console_verification_news_current_base_v1_20260627.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/reporting_console_verification_news_current_base_v1_20260627.md --repo-root .`

## Definition Of Done

- Local Cockpit no longer loads Vercel Analytics by default.
- Verification review selectors do not switch between controlled and
  uncontrolled states.
- News search payloads include a `date_from` value for bounded lookbacks and
  omit it for all-time searches.
- Focused validation and contract checks pass.
- A replacement PR is opened against
  `migration/clean-runtime-baseline-reconstruct-v1`; if local frontend tool
  validation is unavailable, the PR remains draft until GitHub CI passes.
  Issues close only after merge.
