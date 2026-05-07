# Cockpit Home Live Wiring v1

## 1. Branch / HEAD / Worktree / Dirty Status

- Branch: `safe/cockpit-home-live-wiring-v1`
- HEAD: `53b60a71cc21`
- Worktree: `/mnt/sdb2/home/l4nd0/tenn-cockpit-home-live-wiring-v1`
- Dirty status: modified frontend Home files and untracked task card only; `reports/` artifacts are ignored by repo exclude rules.

## 2. Task Card and Registry Status

- Task card created: `docs/agent_tasks/cockpit_home_live_wiring_v1.md`
- Validation: `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_home_live_wiring_v1.md` returned `"ok": true`.
- Latest registry list-active on 2026-05-07 returned `"active_jobs": []`.
- Latest registry overlap check returned `"ok": true`, `"issues": []`.
- Registry list-active on 2026-05-07 returned one active job: `tenn_agent_mcp_v0_audit_scaffold_20260507`.
- Registry overlap decision: proceed for validation. The active MCP job owns `tools/tenn_agent_mcp/**`, `tests/tools/tenn_agent_mcp/**`, and its own report/task-card files; it does not own `cockpit-ui/components/cockpit/home/**`, `cockpit-ui/lib/cockpit-home-*`, or `cockpit-ui/types/cockpit-home.ts`.
- Registry pre-claim overlap: `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_home_live_wiring_v1.md --repo-root /mnt/sdb2/home/l4nd0/tenn-cockpit-home-live-wiring-v1` returned `"ok": true`, `"issues": []`.
- Claim: `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_home_live_wiring_v1.md --repo-root /mnt/sdb2/home/l4nd0/tenn-cockpit-home-live-wiring-v1` returned `"ok": true`.
- Note: a later `heartbeat` found no active record because this CLI registry records the short-lived command process PID; the original claim output and `reports/agent_jobs/cockpit_home_live_wiring_v1/status.json` remain as evidence.
- Release: `python3 scripts/agent_job_registry.py release cockpit_home_live_wiring_v1 --repo-root /mnt/sdb2/home/l4nd0/tenn-cockpit-home-live-wiring-v1` returned `"ok": false`, `"active job not found"`, matching the heartbeat observation that no active record remained.

## 3. Base Commits Verified

- `d6a8f109cf34 feat(reporting): add cockpit home bff route` is an ancestor of HEAD.
- `f7a7454 milestone(reporting): cockpit home contract scaffold` is an ancestor of HEAD.

## 4. Files Changed

- `docs/agent_tasks/cockpit_home_live_wiring_v1.md`
- `cockpit-ui/components/cockpit/home/home-page.tsx`
- `cockpit-ui/components/cockpit/home/market-status-header.tsx`
- `cockpit-ui/components/cockpit/home/source-detail-drawer.tsx`
- `cockpit-ui/components/cockpit/home/contextual-assistant.tsx`
- `cockpit-ui/lib/cockpit-home-api.test.ts`
- `cockpit-ui/lib/cockpit-home-contract.test.ts`
- `cockpit-ui/types/cockpit-home.ts`
- Ignored report artifacts: `reports/agent_jobs/cockpit_home_live_wiring_v1/status.json`, `diff-check.json`, `README.md`

## 5. UI Data-Loading Behavior

- `CockpitHomePage` now fetches same-origin `GET /api/cockpit/home` with `cache: "no-store"`.
- The UI starts in a loading state, then renders the BFF payload directly.
- Fetch failures render `DATA_MISSING`; they do not silently substitute mock data.
- No backend runtime code was edited.

## 6. Loading / Degraded / DATA_MISSING Rendering Behavior

- Loading shows an explicit `Loading Cockpit Home` workspace and `Home BFF: LOADING` data health.
- `PARTIAL`, `DEGRADED`, and `DATA_MISSING` BFF aggregate states show a top banner with backend missing codes.
- Section-level missing states render visible `DATA_MISSING` panels for market movers, news, and attention queue.
- Portfolio null fields render `DATA_MISSING` instead of zero-filled values.

## 7. Mock Fallback Behavior

- Mock sessions remain available only through non-production `DEMO ...` controls.
- Demo mode displays a `DEMO FIXTURE` banner and marks demo news as `UNKNOWN-UNCLASSIFIED`.
- Demo items are unresolvable and blocked from assistant attachment.

## 8. Source-Label and Trust Behavior

- Backend source labels are mapped through the existing taxonomy helper.
- `context_only`, `no_hit`, `missing_required_evidence`, and `degraded_runtime` are not upgraded to verified trust.
- Local personal holdings are labelled in the UI as local personal data and explicitly not canonical financial truth.

## 9. Chat / Source Handoff Behavior

- No new source detail resolver was implemented.
- The source drawer only displays BFF-provided resolver/source metadata.
- Assistant attachment is allowed only when the existing Home contract says the source is resolvable and not blocked by `DATA_MISSING`, degraded, or unresolvable evidence.

## 10. Tests Run and Exact Results

- `pnpm install --frozen-lockfile`: passed; installed locked frontend dependencies in ignored `node_modules`.
- Initial pre-install `npx tsc --noEmit --pretty false`: failed because `node_modules` was absent and `npx` resolved the placeholder package.
- Initial pre-install `pnpm exec tsc --noEmit --pretty false`: failed because local `tsc` was not installed yet.
- `pnpm exec vitest run lib/cockpit-home-api.test.ts lib/cockpit-home-contract.test.ts`: passed, `2 passed (2)`, `13 passed (13)`.
- `pnpm exec tsc --noEmit --pretty false`: passed.
- `npx tsc --noEmit --pretty false`: passed.
- `pnpm exec eslint components/cockpit/home/home-page.tsx components/cockpit/home/market-status-header.tsx components/cockpit/home/source-detail-drawer.tsx components/cockpit/home/contextual-assistant.tsx lib/cockpit-home-api.test.ts lib/cockpit-home-contract.test.ts`: passed.
- `git diff --check`: passed.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_home_live_wiring_v1.md`: passed with `"ok": true`, `"issues": []`, `"disallowed_files": []`.

## 10a. Browser Validation

- Exact server command used: `pnpm exec next dev --hostname 127.0.0.1 --port 3017` from `cockpit-ui/`.
- URL tested: `http://127.0.0.1:3017/`.
- Browser/tool used: Playwright Chromium, headless, via inline `node` validation harness from `cockpit-ui/`.
- Real BFF load: page requested same-origin `/api/cockpit/home`; response status was `200`; response `data_state` was `PARTIAL`; BFF-backed Home state rendered.
- Loading/PARTIAL/DEGRADED/DATA_MISSING findings: route interception of only `/api/cockpit/home` made loading, `PARTIAL`, `DEGRADED`, and `DATA_MISSING` states reachable. Loading text, `Home state: PARTIAL`, `Home state: DEGRADED`, `Home state: DATA_MISSING`, and empty-news `DATA_MISSING` notices were visible.
- Fetch failure finding: intercepted `503` for `/api/cockpit/home` rendered `Cockpit Home BFF unavailable`; mock news did not silently appear; source-backed/verified labels were not shown.
- Mock/demo findings: `DEMO OPEN` rendered the explicit `DEMO FIXTURE` banner and `DEMO_FIXTURE_NOT_SOURCE_BACKED`; demo source drawer showed the item as not source-backed and assistant analysis was disabled.
- Source drawer findings: degraded and no-hit source fixtures opened the drawer with BFF-provided source/evidence metadata; no source-detail resolver call was observed.
- Assistant attachment findings: degraded, no-hit/missing, and demo items all left `Analyze with Tenn Assistant` disabled and displayed a blocked handoff reason.
- Network findings: every browser scenario requested `/api/cockpit/home` exactly once; no legacy `/chat`, `/api/chat`, direct Postgres, direct Qdrant, files, news-store, memory-store, holdings, or commentary-recent browser requests were observed.
- Non-BFF network finding: the app requested `https://va.vercel-scripts.com/v1/script.debug.js` from the root page. This is not a datastore request, but it is a cross-origin non-BFF request observed during Home validation.
- Console findings: browser validation failed the "without console errors" criterion. Console errors included a React hydration mismatch on `<html className="dark">` vs `style={{color-scheme:"dark"}}`, invalid nested `<button>` markup in the app sidebar/chat session controls, and duplicate keys for `market_movers:NO_MARKET_MOVERS_ENDPOINT` and `attention_queue:NO_ATTENTION_QUEUE_ENDPOINT` during the real BFF load. The synthetic `503` fetch-failure scenarios also logged the expected browser resource-load error for `/api/cockpit/home`.
- DATA_MISSING: `graphify-out/GRAPH_REPORT.md` was absent in this isolated worktree when checked, so graphify architecture evidence is unavailable for this validation report.
- Final browser verdict: FAIL, due to console errors and the observed non-BFF analytics script request.
- Safe to commit: NO. Product tests and static checks pass, but browser validation is not clean.

## 10b. Targeted Browser Blocker Triage

- Blocker 1, duplicate Home missing-signal keys: caused by the Cockpit Home live-wiring diff. `cockpit-ui/components/cockpit/home/home-page.tsx` combined aggregate `response.data_missing` with section-level `item.state.data_missing`, then rendered `StateSignalList` entries using `key={`${signal.section}:${signal.code}`}`. This produced duplicate keys for `market_movers:NO_MARKET_MOVERS_ENDPOINT` and `attention_queue:NO_ATTENTION_QUEUE_ENDPOINT`.
- Fix applied: `home-page.tsx` now dedupes `CockpitHomeDataMissingSignal` values by section, code, message, source id, evidence id, and source label before rendering section signals. Render keys now use that full signal identity plus render index. No source IDs, evidence IDs, trust labels, or health states are fabricated.
- Blocker 2, nested-button/hydration console errors: pre-existing shell/sidebar issue, out of scope for this task card. Exact source: `cockpit-ui/components/cockpit/cockpit-sidebar.tsx:380` renders a `SidebarMenuButton` whose implementation is a `button` in `cockpit-ui/components/ui/sidebar.tsx:498`, and it nests a `Button` at `cockpit-ui/components/cockpit/cockpit-sidebar.tsx:393` with `aria-label="Delete chat session"`.
- Additional hydration mismatch: pre-existing layout/theme issue, out of scope for this task card. Browser console points at `cockpit-ui/app/layout.tsx:57`, where the server-rendered `<html lang="en" className="dark">` differs from the client-added `style={{color-scheme:"dark"}}`.
- Blocker 3, Vercel analytics/debug script: pre-existing app layout instrumentation, out of scope for this task card. Exact source: `cockpit-ui/app/layout.tsx:3` imports `Analytics` from `@vercel/analytics/next`; `cockpit-ui/app/layout.tsx:66` renders `<Analytics />`, which requested `https://va.vercel-scripts.com/v1/script.debug.js` in local dev.
- Browser validation after the Home-owned fix used `pnpm exec next dev --hostname 127.0.0.1 --port 3018`, URL `http://127.0.0.1:3018/`, Playwright Chromium headless.
- Browser results after fix: real BFF load and an intercepted duplicate-signal fixture both requested `/api/cockpit/home` exactly once; no legacy `/chat`, `/api/chat`, direct Postgres, Qdrant, files, news-store, memory-store, holdings, or commentary-recent browser requests were observed.
- Duplicate key verdict after fix: PASS. Both browser scenarios reported zero duplicate-key messages.
- Remaining console/network verdict after fix: FAIL, out of scope. The nested-button/hydration errors and Vercel analytics script request remain because their sources are outside the Cockpit Home allowed files.

## 11. Collision Risk

- Expected collision risk: MEDIUM.
- Actual collision risk: MEDIUM.
- No contested backend/runtime surfaces were touched.
- Registry overlap check returned no issues before implementation.

## 12. DATA_MISSING

- Browser validation was performed and failed because console errors were observed.
- The current BFF contract intentionally reports unavailable Home sections as `DATA_MISSING`.
- There is no source detail resolver beyond existing BFF metadata.
- There is no full Home-to-chat source hydration beyond existing attached-source contract support.
- `graphify-out/GRAPH_REPORT.md` is absent in this isolated worktree, so graphify evidence is `DATA_MISSING`.

## 13. Safe to Commit

- Not safe to commit from a full validation perspective.
- Product tests and static checks passed, and the Home-owned duplicate-key browser blocker is fixed.
- Full browser cleanliness still fails due to out-of-scope shell/sidebar/layout and analytics findings.
- Do not commit until explicitly instructed.

## 14. Browser Validation Follow-Up

- Browser validation has now run and failed.
- Next safe step: decide whether to fix the console errors and analytics-script policy issue in a separate approved implementation pass, or explicitly waive those browser findings before commit.

## 15. Project Memory Save Recommendation

- Save a memory note that Cockpit Home web UI is now live-wired to same-origin `GET /api/cockpit/home`, with mock states demoted to explicit non-production demo fixtures and source trust preserved from backend labels.
