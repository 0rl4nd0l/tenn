# Cockpit UI Wait-Then-Actionability Rollout

Job: `cockpit_ui_wait_then_actionability_rollout_v1_20260524`
Date: 2026-05-24
Result: complete; one frontend-only Cockpit News actionability slice implemented

## Confirmed Facts

- Canonical entrypoint: `/home/l4nd0/tenn`.
- Canonical resolved path: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Branch before and after implementation: `migration/clean-runtime-baseline-reconstruct-v1`.
- Initial preflight HEAD before runtime-topology follow-up commits landed: `2811153e6f05e55d3e7989779240cd6a2447458d`.
- Current implementation base before this job commit: `dc9e98bd9cdc596ec829f9860d85119f2f389c44`.
- Appendix 5B gate stack commit is present: `git merge-base --is-ancestor c5e3f7c50ce3cc2f2597a0bfd1406cddeb818967 HEAD` returned `APPENDIX5B_PRESENT`.
- The recent Home actionability report README was not present; only `reports/agent_jobs/cockpit_home_actionability_helper_v1_20260522/diff-check.json` existed.
- Runtime topology reconciliation report exists and says active runtime source paths were reconciled to canonical `/home/l4nd0/tenn`; no runtime changes were made in this job.

## Inferred Facts

- News was the safest non-Home actionability slice because it already exposes query state, search failure, result count, provider, ticker, URL, content snippet, score, and `published_at` when returned.
- News cannot honestly display Home-style `context_only`, claim-verified, financial-truth, source-kind, or chat-handoff states because `/rag/query` results do not provide source labels, source kinds, or evidence labels.
- The CSL design seed is best addressed here as UI evidence-state clarity: filing/context search results now avoid visually implying verified price or technical evidence.

## DATA_MISSING

- No backend News source labels, source kinds, evidence labels, or financial-truth coverage are available in `NewsSearchResult`.
- `published_at` may be absent from returned hits; those results now render as `DATE MISSING` / `DATA_MISSING` rather than receiving a fabricated current date.
- The exact commit hash for this report is not knowable until after committing this report; the final operator response records the created commit hash.

## Wait Loop Summary

- First active registry sample found `runtime_topology_rebind_readiness_impl_v1_20260524`, lane `Evaluation`, task card `docs/agent_tasks/runtime_topology_rebind_readiness_impl_v1_20260524.md`.
- That job owned runtime topology/systemd/cron-adjacent files, so this job did not claim, edit, or create a task card during the first wait interval.
- Waited one 300 second interval.
- Next `list-active` returned an empty `active_jobs` list, so preflight proceeded.
- While this job was later claimed, the separate runtime-topology job completed documentation commits and advanced HEAD from `2811153e` to `dc9e98bd`; status remained clean except this job's allowed files.

## Registry Status

- `python3 scripts/agent_job_registry.py list-active`: empty after wait.
- Initial `check-overlap`: PASS after task card validation.
- Initial `claim`: PASS.
- Task card was narrowed from broad discovery paths to exact News files, then the registry claim was refreshed.
- Active claim after narrowing owned only this task card, this report directory, `news-screen.tsx`, `news-screen.test.tsx`, `cockpit-news-actionability.ts`, and `cockpit-news-actionability.test.ts`.

## Scout Findings

- UI Surface Scout recommended Cockpit News as the best value-to-risk target; Full Chat was deferred as lower benefit and Watchlist was mostly local-only because current rows usually lack source IDs.
- Evidence-State Scout found Home has the strongest evidence model, but Home actionability had already landed. The same scout warned that standalone News must not claim source-backed/context-only states from missing fields.
- Test/Smoke Scout found Watchlist had existing component tests, but advised adding a focused `news-screen.test.tsx` if News was chosen.
- Collision Scout found no unrelated active jobs or dirty tracked files after the wait; only this task card and this job's ignored status artifact were task-owned dirt.

## Debate And Reconciliation

- Candidate surface A, News: chosen. It is the preferred candidate, gives immediate actionability value, and can stay frontend-only by deriving states from existing search state and result fields.
- Candidate surface B, Full Chat handoff: deferred. It already consumes Home source handoff params safely, and changing the main streaming chat flow has a larger blast radius.
- Candidate surface C, Watchlist: deferred. It has the easiest tests but weaker evidence-state inputs; most clarity would honestly say `local watchlist only`.
- Chosen surface: Cockpit News.
- Why smallest/highest-value: one component, one helper, focused tests, no backend routes, no data-store changes, no runtime topology changes.

## Files Inspected

- `cockpit-ui/components/cockpit/news/news-screen.tsx`
- `cockpit-ui/components/cockpit/watchlist/watchlist-screen.tsx`
- `cockpit-ui/components/cockpit/chat/chat-screen.tsx`
- `cockpit-ui/components/cockpit/chat/terminal-message.tsx`
- `cockpit-ui/components/cockpit/home/home-page.tsx`
- `cockpit-ui/components/cockpit/home/source-detail-drawer.tsx`
- `cockpit-ui/lib/cockpit-home-actionability.ts`
- `cockpit-ui/lib/cockpit-home-contract.ts`
- `cockpit-ui/lib/cockpit-home-api.ts`
- `cockpit-ui/lib/cockpit-types.ts`
- `cockpit-ui/types/cockpit-home.ts`
- `cockpit-ui/package.json`
- `cockpit-ui/vitest.config.ts`
- `cockpit-ui/playwright.config.ts`
- `reports/agent_jobs/runtime_topology_reconciliation_impl_v1_20260524/README.md`

## Files Changed

- `docs/agent_tasks/cockpit_ui_wait_then_actionability_rollout_v1_20260524.md`
- `cockpit-ui/components/cockpit/news/news-screen.tsx`
- `cockpit-ui/components/cockpit/news/news-screen.test.tsx`
- `cockpit-ui/lib/cockpit-news-actionability.ts`
- `cockpit-ui/lib/cockpit-news-actionability.test.ts`
- `reports/agent_jobs/cockpit_ui_wait_then_actionability_rollout_v1_20260524/README.md`
- `reports/agent_jobs/cockpit_ui_wait_then_actionability_rollout_v1_20260524/diff-check.json`
- `reports/agent_jobs/cockpit_ui_wait_then_actionability_rollout_v1_20260524/status.json`

## Before And After

Before:

- News Search rendered controls, errors, result count, backend badge, and individual results.
- Missing `published_at` was mapped to `new Date()`, which could make undated results look fresh.
- Duplicate returned filings/notices were not surfaced visually.
- Results with URLs and snippets were not clearly distinguished from verified financial or market-data evidence.

After:

- News shows a compact `News evidence state` panel.
- States include `DATA_MISSING`, `SEARCHING`, `DEGRADED`, `UNRESOLVED`, `STALE`, `DUPLICATED`, `PARTIAL`, and `SOURCE READY`.
- Per-result badges distinguish `SOURCE LINK`, `SNIPPET ONLY`, `DATE MISSING`, `STALE`, and `DUPLICATE xN`.
- Missing `published_at` stays explicit as `published_at DATA_MISSING`.
- Duplicate groups are summarized so repeated filing notices can be treated as one evidence cluster.
- Copy explicitly says source links are inspectable context, not verified financial truth.

## Evidence-State Honesty Proof

- No backend field was added or required.
- No backend API, storage, Qdrant, news DB, memory, extraction, parser, Docker, systemd, or cron file changed.
- The helper uses only existing frontend fields: query state, search error, result count, `url`, `date`, `publishedAtMissing`, `headline`, and `source`.
- The UI never upgrades News results to claim-verified, financial-truth, or context-only source labels.

## Validation Commands And Results

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_ui_wait_then_actionability_rollout_v1_20260524.md`: PASS.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_ui_wait_then_actionability_rollout_v1_20260524.md`: PASS.
- `corepack pnpm --dir cockpit-ui exec vitest run lib/cockpit-news-actionability.test.ts components/cockpit/news/news-screen.test.tsx`: PASS, 2 files / 7 tests.
- `corepack pnpm --dir cockpit-ui exec eslint components/cockpit/news/news-screen.tsx components/cockpit/news/news-screen.test.tsx lib/cockpit-news-actionability.ts lib/cockpit-news-actionability.test.ts`: PASS.
- `git diff --check`: PASS.
- `corepack pnpm --dir cockpit-ui exec tsc -p tsconfig.json --noEmit --incremental false`: PASS.
- `COCKPIT_E2E_BASE_URL=http://127.0.0.1:8081 corepack pnpm --dir cockpit-ui exec playwright test tests/smoke.spec.ts --project=chromium --output=/tmp/cockpit-ui-smoke-results-actionability`: PASS, 4 tests. Port 3000 was unavailable; existing canonical Cockpit UI listener on port 8081 was used.
- `corepack pnpm --dir cockpit-ui build`: PASS.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_ui_wait_then_actionability_rollout_v1_20260524.md`: PASS before this final report update.

## Commit

- Commit hash: recorded in final response after the scoped commit is created.
- Planned commit subject: `feat(reporting): extend cockpit actionability states`.

## Final Git Status

- To be sampled after commit and registry release.

## Remaining Blockers

- Standalone News still cannot show backend source labels or verified market-data coverage without a separate backend/API contract.
- `lookback` remains UI state and is not wired into the `/rag/query` request in this slice.

## Recommended Next Task

Add backend-provided News evidence labels and freshness metadata to the `/rag/query` result contract, then update the News actionability helper to consume those fields without inferring them locally.

## Project Memory Save Recommendation

Save that Cockpit News actionability now has a frontend-only helper and tests, and that standalone News must not claim Home-style source labels until the backend result contract provides them.
