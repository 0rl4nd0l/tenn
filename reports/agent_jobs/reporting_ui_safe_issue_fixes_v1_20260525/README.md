# Reporting UI Safe Issue Fixes

## Result

Status: complete for the bounded safe issue bundle.

Fixed GitHub issues:

- #45: local Cockpit no longer renders Vercel Analytics unless `VERCEL=1` or `ENABLE_VERCEL_ANALYTICS=1`.
- #47: optional Verification Select values now stay controlled with sentinel values.
- #48: Verification saved-review sidebar rows stay inside the right sidebar at `1440x1000`.
- #52: Marketplace helper missing-token state no longer renders a dead `href="#"`; valid token links install a real bookmarklet after mount without hydration warnings.
- #44: Home PARTIAL banner now shows `+N more` when more than three missing signals exist, with the full list available in the title.

## Safety Scope

Lane: Reporting.
Execution mode: SAFE EXTENSION.
Production data access: false.

No backend route behavior, data contracts, financial truth, extraction, parser routing, query routing, memory stores, DB, Qdrant, news stores, Docker, env files, runtime services, or Strategy Lab components were changed.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/reporting_ui_safe_issue_fixes_v1_20260525.md`: passed.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/reporting_ui_safe_issue_fixes_v1_20260525.md`: passed.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/reporting_ui_safe_issue_fixes_v1_20260525.md`: passed.
- `corepack pnpm install --frozen-lockfile`: passed; no lockfile changes.
- `corepack pnpm exec eslint app/marketplace-capture/page.tsx app/layout.tsx components/cockpit/verification/tabs/review-tab-panel.tsx components/cockpit/verification/verification-sidebar.tsx components/cockpit/home/home-page.tsx --max-warnings=0`: passed.
- `corepack pnpm exec tsc --noEmit --pretty false`: passed.
- `corepack pnpm test`: failed on unrelated existing non-allowlisted Strategy Lab and marketplace assistant expectations; see `status.json`.
- Browser smoke at `http://127.0.0.1:3100`: passed for missing-token helper state, valid bookmarklet href, analytics absence, Verification Select warning absence, Verification sidebar saved-review overflow, and Home `+3 more` disclosure.
- `git diff --check`: passed.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/reporting_ui_safe_issue_fixes_v1_20260525.md`: passed.

## Notes

The browser validation briefly rewrote `cockpit-ui/next-env.d.ts` and produced Playwright snapshot files. Those generated artifacts were removed/reverted before final diff validation.

