# Chat Evidence Actionability And CSL Guard

Job: `chat_evidence_actionability_and_csl_guard_v1_20260524`
Date: 2026-05-24
Status: complete; frontend chat evidence-state helper and CSL-style regression guard implemented, with continuation hardening for no-hit market-tool evidence

Lane: Query Orchestration
Branch: migration/clean-runtime-baseline-reconstruct-v1
Worktree: /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1
Execution mode: AUDIT-FIRST SAFE EXTENSION
Contested surfaces touched:
- `cockpit-ui/components/cockpit/chat/terminal-message.tsx`
- `cockpit-ui/components/cockpit/chat/terminal-message.test.tsx`
Collision risk: MEDIUM after narrowing
Decision: proceed with frontend chat rendering/tests only

## Confirmed Facts

- Canonical entrypoint command used: `cd /home/l4nd0/tenn`.
- Canonical resolved path: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Branch before implementation: `migration/clean-runtime-baseline-reconstruct-v1`.
- HEAD before implementation: `016f613f39c944e312f947c1f2c06d3ec0fdce48`.
- Latest commit before implementation was `016f613f feat(reporting): extend cockpit actionability states`.
- Appendix 5B gate stack commit is present: `c5e3f7c50ce3cc2f2597a0bfd1406cddeb818967`.
- News actionability UI commit is present and was the starting HEAD: `016f613f39c944e312f947c1f2c06d3ec0fdce48`.
- Runtime topology reconciliation report exists and states active runtime source paths were reconciled to canonical `/home/l4nd0/tenn`; this job made no runtime topology change.
- Cockpit web chat route ownership is clear: `/full-chat` renders `ChatScreen`, which calls `sendChatMessage`/`streamChat` in `cockpit-ui/lib/api-client.ts`, both targeting `/api/cockpit/chat`.
- Backend route ownership is clear: `financial-engine_v2/backend/app/routes/cockpit_api.py` owns `@router.post("/chat")` and builds visible-source/UI metadata via `_enforce_visible_source_contract()` and `_build_chat_ui_metadata()`.
- A legacy backend route still exists at `financial-engine_v2/backend/app/routes/chat.py`, but the current Cockpit web chat surface inspected here uses `/api/cockpit/chat`.
- Existing backend evidence labels include `claim_verified`, `context_only`, `no_hit`, `degraded_runtime`, `missing_required_evidence`, `local_personal_data`, `memory_context`, `external_web_context`, `financial_truth`, and `unknown_unclassified`.
- Current code can discuss `price_state.trend_regime`, including in `financial-engine_v2/cockpit/core/chat.py`; this slice did not modify backend synthesis.
- Continuation audit found backend UI sources can include `tv_screener:` source ids with `no_hit`/`operational_no_hit` labels when a screener returns no rows; these must not satisfy market-price evidence for price-trend claims.

## Inferred Facts

- The safest high-value slice was frontend evidence-state clarity because `TerminalMessage` already receives evidence labels, missing categories, source coverage status, visible sources, and claim-verified counts.
- A backend answer guard would be valuable, but editing `financial-engine_v2/backend/app/routes/cockpit_api.py` or `financial-engine_v2/cockpit/core/chat.py` would touch contested runtime/chat surfaces and exceed the narrowed safe-extension slice.
- The CSL seed failure class can be covered without production data by a synthetic assistant message that contains a bearish/current price-trend claim while visible evidence is only a context-only filing/buy-back notice.
- Missing market data and missing metric extraction should be surfaced as actionability gaps in the chat answer shell rather than silently omitted or upgraded to source-backed evidence.

## DATA_MISSING

- `graphify-out/GRAPH_REPORT.md` was not present in this checkout, so no graphify community report could be consulted.
- `reports/agent_jobs/cockpit_home_actionability_helper_v1_20260522/README.md` was not present; only adjacent job artifacts were available.
- The exact historic CSL answer payload that produced the observed bearish trend claim was not found in tests, fixtures, or reports during this run.
- Hidden market evidence for the original observed CSL answer remains DATA_MISSING. The current-code risk is that backend `price_state` can influence answer text while the visible source list can still look filing/context-only; the implemented regression captures that generic mismatch class.
- The final commit hash cannot be embedded inside this committed report without changing the commit hash; the final operator response records the immutable hash after commit.

## Registry Status

- Initial `python3 scripts/agent_job_registry.py list-active`: empty.
- Initial `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/chat_evidence_actionability_and_csl_guard_v1_20260524.md`: PASS.
- The task card was narrowed from broad discovery paths to exact frontend chat helper/rendering/test files before implementation.
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/chat_evidence_actionability_and_csl_guard_v1_20260524.md`: PASS after adding `allow_unapproved_safe_extension: true`.
- Registry claim after narrowing: PASS.
- A stale self-owned claim from this same job was released during claim refresh; no unrelated active job was present.
- Initial implementation wait behavior: no overlapping active job was present during the implementation job's own claim window.
- Continuation wait behavior: a same-job active record appeared while this follow-up session was auditing; target files were dirty and the heartbeat refreshed, so this session waited through three 300-second registry holds before the active job released and the worktree became clean.
- Continuation claim after release: PASS.
- Initial implementation release command reported `active job not found` because the shared registry already had no active record for that run.
- Continuation final release/list-active is recorded in the final operator response after the hardening commit is created.

## Scout Findings

- Chat Route Scout: current Cockpit web chat uses `/full-chat` -> `ChatScreen` -> `/api/cockpit/chat`; backend UI metadata is assembled in `cockpit_api.py`.
- CSL Seed Regression Scout: no exact stored CSL answer was found. Current-code price trend text can be derived from `price_state.trend_regime`; the safe fixture therefore targets the generic condition "price/technical trend claim plus no visible market-price evidence."
- Evidence Taxonomy Scout: required labels were partly present already, but explicit `market_data_missing`, `metric_extraction_missing`, `draft_only`, `snippet_only`, and `unsupported_or_not_verified` needed frontend normalization for the chat answer shell.
- UI Actionability Scout: `TerminalMessage` was the smallest useful surface. The source drawer is for attached/recent source reattachment and was not the right place for per-answer evidence state.
- Test Scout: focused Vitest helper/component tests were the strongest practical coverage without live production data, Qdrant/news mutation, or backend route edits.

## Pre-Implementation Decision

Candidate A, backend answer/evidence guard: deferred for this slice. The current Cockpit web route is `financial-engine_v2/backend/app/routes/cockpit_api.py`, a contested surface outside the narrowed allowed implementation files. Editing it would raise collision risk from MEDIUM-HIGH to HIGH.

Candidate B, frontend chat evidence-state panel/badges: chosen. `TerminalMessage` already consumes answer metadata, source labels, claim-verified counts, source coverage status, and missing categories, so a focused helper can surface `context_only`, `market_data_missing`, `metric_extraction_missing`, `degraded_runtime`, and unsupported/not-verified states without touching retrieval, synthesis, stores, runtime, or parser routing.

Candidate C, tests-only CSL regression guard: included as focused UI/helper fixtures. The fixture is synthetic and does not require live CSL data, production DB access, Qdrant/news mutation, or external web.

Candidate D, source drawer/actionability copy refinement: deferred. The relevant per-answer surface is the terminal message analyst shell, not the recent-source reattachment drawer.

Decision: proceed with a small frontend helper and `TerminalMessage` rendering/tests only.

## Files Inspected

- `CLAUDE.md`
- `docs/architecture/SYSTEM_CONTRACT.md`
- `/home/l4nd0/.claude/projects/-mnt-sdb2-home-l4nd0-tenn/memory/MEMORY.md`
- `docs/agent_tasks/chat_evidence_actionability_and_csl_guard_v1_20260524.md`
- `reports/agent_jobs/cockpit_ui_wait_then_actionability_rollout_v1_20260524/README.md`
- `reports/agent_jobs/runtime_topology_reconciliation_impl_v1_20260524/README.md`
- `reports/agent_jobs/appendix5b_prm_gate_stack_canonical_integration_v1_20260524/README.md`
- `cockpit-ui/app/full-chat/page.tsx`
- `cockpit-ui/components/cockpit/chat/chat-screen.tsx`
- `cockpit-ui/components/cockpit/chat/terminal-message.tsx`
- `cockpit-ui/components/cockpit/chat/terminal-message.test.tsx`
- `cockpit-ui/components/cockpit/news/news-screen.tsx`
- `cockpit-ui/components/cockpit/home/home-page.tsx`
- `cockpit-ui/components/cockpit/home/source-detail-drawer.tsx`
- `cockpit-ui/lib/api-client.ts`
- `cockpit-ui/lib/cockpit-home-actionability.ts`
- `cockpit-ui/lib/cockpit-news-actionability.ts`
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/backend/app/routes/chat.py`
- `financial-engine_v2/backend/app/services/cockpit_service.py`
- `financial-engine_v2/cockpit/core/chat.py`
- `financial-engine_v2/cockpit/core/tools.py`
- `financial-engine_v2/backend/tests/test_build_ui_sources.py`
- `financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py`

## Files Changed

- `docs/agent_tasks/chat_evidence_actionability_and_csl_guard_v1_20260524.md`
- `cockpit-ui/lib/cockpit-chat-actionability.ts`
- `cockpit-ui/lib/cockpit-chat-actionability.test.ts`
- `cockpit-ui/components/cockpit/chat/terminal-message.tsx`
- `cockpit-ui/components/cockpit/chat/terminal-message.test.tsx`
- `reports/agent_jobs/chat_evidence_actionability_and_csl_guard_v1_20260524/README.md`
- `reports/agent_jobs/chat_evidence_actionability_and_csl_guard_v1_20260524/diff-check.json`

## Implementation Summary

- Added `deriveChatEvidenceActionability()` in `cockpit-ui/lib/cockpit-chat-actionability.ts`.
- The helper normalizes current answer/source metadata into compact states: `claim_verified`, `context_only`, `no_hit`, `market_data_missing`, `metric_extraction_missing`, `degraded_runtime`, `local_personal_data`, `memory_context`, `external_web_context`, `demo_mock`, `unresolved_source`, `snippet_only`, `draft_only`, and `unsupported_or_not_verified`.
- The helper treats price/technical trend claims as `market_data_missing` unless visible sources include market/price evidence by source id, source kind/doc type, or evidence label.
- The helper does not count no-hit, missing-required-evidence, degraded-runtime, `operational_no_hit`, or `runtime_failure` sources as market/price evidence even if their source id has a market-tool prefix.
- The helper maps missing financial rows/financial categories to `metric_extraction_missing`.
- `TerminalMessage` now renders a compact `Evidence state` badge row near the answer header and merges helper gaps/actions into the existing gaps/actionability block.
- Suggested next actions are UI/copy only and disabled: `Pull market data`, `Run metric extraction`, and `Review filing group`.
- No backend routes, retrieval ranking, Qdrant/news stores, memory stores, financial truth writes, parser routing, runtime topology, Docker, cron, model, or GPU config changed.

## Before And After

Before:

- A chat answer with context-only filings could display filing evidence without an explicit visible warning that a price/technical trend claim lacked visible market-price evidence.
- Missing financial rows could appear as a generic missing-data gap without a dedicated metric-extraction state.
- Degraded runtime labels were present in backend metadata, but the chat answer shell did not render a compact per-answer evidence-state panel.

After:

- A CSL-style answer that says "bearish/current price trend" while visible evidence is only a context-only filing renders `Evidence state`, `Market data missing`, `Context only`, and `Unsupported / not verified`.
- The same answer shows `market_data_missing` in the gaps block and a disabled `Pull market data` next action.
- Missing financial rows or `financials` missing categories render `Metric extraction missing` and a disabled `Run metric extraction` next action.
- Degraded runtime renders `Degraded runtime`, `Runtime degraded`, and the `degraded_runtime` gap rather than being hidden behind context labels.
- Claim-verified labels are still shown only when metadata/source fields actually provide claim-verified support.

## Regression Fixtures Added

- `cockpit-ui/lib/cockpit-chat-actionability.test.ts`: synthetic CSL filing-only bearish/current price trend fixture proves context-only filings do not count as market-price evidence.
- `cockpit-ui/lib/cockpit-chat-actionability.test.ts`: visible price source fixture proves market data is not marked missing when a price source is actually surfaced.
- `cockpit-ui/lib/cockpit-chat-actionability.test.ts`: filing text that merely mentions "share price" does not count as market-price evidence.
- `cockpit-ui/lib/cockpit-chat-actionability.test.ts`: no-hit TradingView/screener source ids do not count as market-price evidence.
- `cockpit-ui/lib/cockpit-chat-actionability.test.ts`: missing financial rows map to `metric_extraction_missing`.
- `cockpit-ui/lib/cockpit-chat-actionability.test.ts`: degraded runtime remains visible.
- `cockpit-ui/components/cockpit/chat/terminal-message.test.tsx`: CSL filing-only price-trend claim renders `Market data missing`, `Context only`, `Unsupported / not verified`, `market_data_missing`, and `Pull market data (not connected)` while not rendering `Claim-supported` or `Verified sources`.
- `cockpit-ui/components/cockpit/chat/terminal-message.test.tsx`: degraded runtime evidence state renders without being upgraded to claim-supported evidence.

## Evidence-State Honesty Proof

- Context-only filings do not verify price trend: the CSL fixture uses only a filing/buy-back source with `context_only` labels and no price source id; the helper and UI both mark `market_data_missing` and `unsupported_or_not_verified`.
- No-hit market tools do not verify price trend: a `tv_screener:` source with `no_hit`/`operational_no_hit` metadata still leaves `hasMarketPriceEvidence=false` and surfaces `market_data_missing`.
- Missing market data is surfaced: helper tests assert `market_data_missing` and `Pull market data`; component tests assert the same state appears in the rendered chat shell.
- Missing metric extraction is surfaced: helper tests assert `metric_extraction_missing`, and the rendered missing-data test asserts `Metric extraction missing` and `Run metric extraction (not connected)`.
- Degraded runtime is not hidden: helper and component tests assert `degraded_runtime`/`Degraded runtime` remains visible and is not shown as claim-supported.
- Claim verification is not weakened: claim-verified helper tests require explicit `claim_verified` metadata/source support, and the CSL fixture asserts `claim_verified` is absent.

## No Forbidden Surface Proof

- Changed paths are limited to the narrowed task card allowlist plus ignored job report artifacts.
- Proper combined changed-path grep returned no forbidden path matches for `financial-engine_v2`, Qdrant, memory, news, extraction, Docker, systemd, cron, compose, or `.env`.
- Backend compile validation was not required because no backend Python file changed.
- No database, Qdrant, news.sqlite, memory, financial-truth, extraction, parser-routing, runtime, Docker, cron, model, or GPU files were modified.

## Validation Commands And Results

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/chat_evidence_actionability_and_csl_guard_v1_20260524.md`: PASS.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/chat_evidence_actionability_and_csl_guard_v1_20260524.md`: PASS.
- `corepack pnpm --dir cockpit-ui exec vitest run lib/cockpit-chat-actionability.test.ts components/cockpit/chat/terminal-message.test.tsx`: PASS, 2 files / 21 tests after continuation hardening.
- `corepack pnpm --dir cockpit-ui exec eslint components/cockpit/chat/terminal-message.tsx components/cockpit/chat/terminal-message.test.tsx lib/cockpit-chat-actionability.ts lib/cockpit-chat-actionability.test.ts`: PASS.
- `corepack pnpm --dir cockpit-ui exec tsc -p tsconfig.json --noEmit --incremental false`: PASS.
- `git diff --check`: PASS.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/chat_evidence_actionability_and_csl_guard_v1_20260524.md`: PASS.
- `corepack pnpm --dir cockpit-ui build`: PASS.
- `COCKPIT_E2E_BASE_URL=http://127.0.0.1:8081 corepack pnpm --dir cockpit-ui exec playwright test tests/smoke.spec.ts --project=chromium`: PASS, 4 tests. Existing canonical UI listener on port 8081 was used; no dev server/runtime topology change was made.
- `python3 scripts/agent_job_registry.py release chat_evidence_actionability_and_csl_guard_v1_20260524`: active job not found; shared registry already had no active record.
- `python3 scripts/agent_job_registry.py list-active`: PASS, empty `active_jobs`.

## Commit

- Initial implementation commit: `370c7c99d86795932ab7a543d42b12ffb33c5828` (`feat(reporting): add chat evidence actionability states`).
- Continuation hardening commit: recorded in final response after this report update and validation are committed.

## Final Git Status

- Final status is sampled in the final operator response after the report/task-card amendments are folded into the scoped commit.

## Remaining Blockers

- Exact historic CSL answer payload remains DATA_MISSING.
- A backend synthesis guard for hidden `price_state` versus visible source evidence remains a separate higher-risk task because it touches contested chat route/synthesis files.
- Source drawer taxonomy polish was deferred because the relevant per-answer actionability surface is `TerminalMessage`.

## Recommended Next Task

Add a backend-side chat response metadata guard that explicitly emits `market_data_missing` when answer text includes price/technical trend claims but the delivered visible source envelope lacks market-price evidence. Keep it limited to `cockpit_api.py`/chat response metadata tests and do not mutate data stores or retrieval ranking.

## Project Memory Save Recommendation

Save that Cockpit chat now has a frontend-only `cockpit-chat-actionability` helper and fixtures that prevent context-only filing evidence from visually verifying price/technical trend claims. Also save that backend hidden-price-state enforcement remains a recommended follow-up, not completed in this slice.

## Required Final Report Template

Files changed:
- `docs/agent_tasks/chat_evidence_actionability_and_csl_guard_v1_20260524.md`
- `cockpit-ui/lib/cockpit-chat-actionability.ts`
- `cockpit-ui/lib/cockpit-chat-actionability.test.ts`
- `cockpit-ui/components/cockpit/chat/terminal-message.tsx`
- `cockpit-ui/components/cockpit/chat/terminal-message.test.tsx`
- `reports/agent_jobs/chat_evidence_actionability_and_csl_guard_v1_20260524/README.md`
- `reports/agent_jobs/chat_evidence_actionability_and_csl_guard_v1_20260524/diff-check.json`

Files inspected:
- See "Files Inspected".

Lane:
- Query Orchestration

Execution mode:
- AUDIT-FIRST SAFE EXTENSION

Collision risk:
- MEDIUM

Validation run:
- See "Validation Commands And Results".

Validation result:
- Passed focused frontend validation, build, smoke, and task-card contract checks.

Files intentionally not touched:
- Backend chat routes/services
- Query orchestrator/retrieval ranking
- Source drawer taxonomy beyond chat message display
- Financial truth/extraction/parser routing
- Memory services
- Qdrant/news stores
- Runtime topology, Docker, cron, model/GPU config

Remaining blockers:
- Original CSL transcript/payload not found.
- Backend synthesis guard still recommended as a separate safe task.

Next safe step:
- Add backend synthesis/evidence-envelope tests for market trend verification if a clean task-card lane can own the backend chat surface.
