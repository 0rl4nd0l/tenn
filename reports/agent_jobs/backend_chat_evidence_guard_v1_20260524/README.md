# Backend Chat Evidence Guard

Job: `backend_chat_evidence_guard_v1_20260524`
Date: 2026-05-24
Status: complete; implementation committed and registry lock released

Lane: Query Orchestration
Supporting lanes: Provenance, Reporting, Evaluation
Branch: `safe/backend-chat-evidence-guard-v1-20260524`
Worktree: `/home/l4nd0/tenn-backend-chat-evidence-guard-v1-20260524`
Execution mode: AUDIT-FIRST SAFE EXTENSION
Collision risk: MEDIUM-HIGH, reduced by isolated worktree and narrowed task card
Decision: proceed with deterministic backend metadata guard only

## Confirmed Facts

- Canonical `/home/l4nd0/tenn` resolves to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Shared checkout branch was `migration/clean-runtime-baseline-reconstruct-v1` at `0552a9eb5955f94b9842111c5e9a53fae8260e4b`.
- Isolated implementation branch is `safe/backend-chat-evidence-guard-v1-20260524` from the same HEAD.
- Required commits were present on the implementation base: Appendix 5B `c5e3f7c50ce3cc2f2597a0bfd1406cddeb818967`, News actionability `016f613f39c944e312f947c1f2c06d3ec0fdce48`, and Chat UI guard `370c7c99d86795932ab7a543d42b12ffb33c5828`.
- Active Cockpit web chat route is `POST /api/cockpit/chat` in `financial-engine_v2/backend/app/routes/cockpit_api.py`.
- Legacy `/chat` and `/api/chat` routes still exist in `financial-engine_v2/backend/app/routes/chat.py`, but the current Cockpit web UI path uses `/api/cockpit/chat`.
- `_enforce_visible_source_contract()` blocked missing visible sources, but any non-operational visible source could still let a claim through even when its evidence category did not match the claim.
- Existing frontend actionability already displays `market_data_missing`, `metric_extraction_missing`, `context_only`, and `unsupported_or_not_verified` when backend metadata or visible-source heuristics expose those states.

## Contract Check

- Target layer: Analysis/Client response metadata for backend chat delivery.
- Relevant contract rules: backend remains authority; no Cockpit-side retrieval; no data fabrication; fail-visible missing evidence; no runtime/model/topology changes.
- Must not change: retrieval ranking, Qdrant/news/memory stores, extraction truth, canonical financial rows, parser routing, Docker/systemd/cron/model/GPU config.
- Safety rationale: the change is pure metadata enrichment after visible sources are already built. It does not retrieve, rank, mutate, remove sources, or rewrite answer text.

## Scout Findings

- Route scout: current web flow is frontend `/api/cockpit/chat` -> backend `cockpit_api.cockpit_chat()` -> `CockpitService.chat_stream()` -> `ChatController.build_chat_response()`; metadata is built in `_build_chat_ui_metadata()` for both stream and non-stream delivery.
- Evidence-envelope scout: backend already has labels such as `claim_verified`, `context_only`, `no_hit`, `financial_truth`, `degraded_runtime`, and `missing_required_evidence`; the missing piece was deterministic mapping from detected claim family to required visible evidence category.
- Claim scout: `ChatController` can synthesize from hidden `price_state`, while the visible-source builder exposes price evidence only when actual price/price-query tool payloads become visible sources. This matches the CSL-style filing-only price-trend mismatch.
- CSL scout: no exact production CSL payload was found; the regression uses a synthetic generic fixture with CSL, context-only Appendix 3C buy-back filing evidence, no market-price source, and bearish/current price-trend text.
- Test scout: focused offline backend tests can run through pure helper tests plus FastAPI route tests without production DB, Qdrant, news, memory, runtime, or external web.

## Parent Reconciliation

- Option A, prompt-only guard: rejected. Prompt text cannot reliably enforce claim/evidence matching and would not cover generated or legacy responses.
- Option B, post-synthesis claim/evidence validator: chosen. It is deterministic, testable, and runs after visible sources are available.
- Option C, evidence-envelope metadata normalizer: partially included. The helper enriches existing metadata labels and missing categories without changing the envelope contract.
- Option D, frontend-only continuation: rejected for this task. The prior UI slice already exists; backend metadata now needs to carry the guard before the UI receives the response.

## Implementation

- Added `financial-engine_v2/backend/app/services/chat_evidence_guard.py`.
- The helper detects claim families: `market_price_or_technical_trend`, `financial_metric`, `filing_context`, `buyback_activity`, `tariff_regulatory`, and `local_holdings`.
- The helper classifies visible sources into evidence categories including `market_data`, `price_series`, `technical_indicator`, `extracted_metric`, `financial_statement`, `filing`, `buyback_filing`, `regulatory_source`, `news`, `local_personal_data`, `no_hit`, and `degraded_runtime`.
- Integrated `enrich_chat_metadata_with_evidence_guard()` inside `_build_chat_ui_metadata()`, after source label counts and base source coverage are computed.
- Unsupported market/technical claims now add `market_data_missing`, `missing_required_evidence`, `unsupported_or_not_verified`, `missing_evidence_categories=["market_data"]`, and `source_coverage_status="missing_required_evidence"` unless a higher-priority degraded/local-personal status applies.
- Unsupported financial metric claims now add `metric_extraction_missing` and `missing_evidence_categories=["metric_extraction"]`.
- Filing-supported buyback/tariff claims remain `context_only` unless explicitly claim-verified; repeated filing notices do not become market-price evidence.
- Degraded runtime labels remain visible and keep `source_coverage_status="degraded_runtime"`.
- No answer text is rewritten in this slice.

## Tests Added

- `test_chat_evidence_guard.py`
  - Filing-only context cannot verify bearish/current price-trend claims.
  - Visible price source satisfies market/price/technical requirements.
  - Missing financial statements produce `metric_extraction_missing`.
  - Financial-truth source satisfies metric requirements.
  - Buyback/tariff filing claims remain context-only when filing-supported.
  - No-hit market tools do not satisfy price-trend evidence.
  - Degraded runtime remains visible.
  - Claim-verified status is demoted at response metadata level when required market evidence is missing.
- `test_cockpit_api_chat_stream.py`
  - Non-streaming `/api/cockpit/chat` returns `market_data_missing` metadata for CSL-style filing-only price-trend claim.
  - Streaming `/api/cockpit/chat` returns the same metadata in the SSE `done` event before the UI sees final metadata.
  - Non-streaming `/api/cockpit/chat` returns `metric_extraction_missing` for metric claims with only context filings.

## Before And After

Before:

- A context-only filing source could be visible while answer text made a bearish/bullish/technical price-trend claim.
- Overall source coverage could remain `context_only` or appear source-backed without a backend-level missing-market-evidence label.
- Missing financial rows could remain generic missing evidence rather than a metric-extraction-specific state.

After:

- CSL-style filing-only bearish price-trend text reaches the UI with `market_data_missing` and `unsupported_or_not_verified`.
- Metric claims without extracted metric/financial statement evidence reach the UI with `metric_extraction_missing`.
- No-hit/context-only sources do not satisfy market-price evidence.
- Degraded runtime remains visible and is not hidden by missing-evidence relabeling.

## DATA_MISSING

- `graphify-out/GRAPH_REPORT.md` is absent in this worktree.
- The exact historic CSL chat payload was not found in repo tests/reports; the regression is synthetic and generic.
- `financial-engine_v2/backend/tests/test_query_orchestrator.py` has a pre-existing baseline failure at `test_company_analysis_keeps_announcement_context_when_financial_rows_missing`; the same focused test fails on the unchanged canonical checkout, so this task did not broaden into QueryOrchestrator sufficiency logic.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/backend_chat_evidence_guard_v1_20260524.md`: PASS.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/backend_chat_evidence_guard_v1_20260524.md`: PASS.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/backend_chat_evidence_guard_v1_20260524.md`: PASS.
- `python3 -m compileall financial-engine_v2/backend/app/services/chat_evidence_guard.py financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_chat_evidence_guard.py financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py`: PASS.
- `/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_chat_evidence_guard.py financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py financial-engine_v2/backend/tests/test_build_ui_sources.py -q`: PASS, `110 passed`.
- `/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python -m ruff check financial-engine_v2/backend/app/services/chat_evidence_guard.py financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_chat_evidence_guard.py financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py`: PASS.
- `git diff --check`: PASS.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/backend_chat_evidence_guard_v1_20260524.md`: PASS.
- `python3 -m json.tool reports/agent_jobs/backend_chat_evidence_guard_v1_20260524/status.json`: PASS.
- `python3 -m json.tool reports/agent_jobs/backend_chat_evidence_guard_v1_20260524/diff-check.json`: PASS.
- `python3 scripts/agent_job_registry.py release backend_chat_evidence_guard_v1_20260524`: PASS.
- Final `python3 scripts/agent_job_registry.py list-active`: backend guard job absent; unrelated `task_card_dirt_hygiene_v1_20260524` active in the shared canonical worktree.
- Broader `/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_query_orchestrator.py -q`: FAIL, one pre-existing unrelated failure also reproduced on the unchanged canonical checkout.
- Forbidden-surface grep over changed paths found no Qdrant/news/memory/extraction/parser/runtime/Docker/systemd/cron/model/GPU paths.

## Files Changed

- `docs/agent_tasks/backend_chat_evidence_guard_v1_20260524.md`
- `financial-engine_v2/backend/app/services/chat_evidence_guard.py`
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/backend/tests/test_chat_evidence_guard.py`
- `financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py`
- `reports/agent_jobs/backend_chat_evidence_guard_v1_20260524/README.md`

## Files Inspected

- `CLAUDE.md`
- `docs/architecture/SYSTEM_CONTRACT.md`
- `docs/entrypoints.md`
- `docs/architecture/13_security_and_secrets.md`
- `/home/l4nd0/.claude/projects/-mnt-sdb2-home-l4nd0-tenn/memory/MEMORY.md`
- `/home/l4nd0/.codex/memories/MEMORY.md`
- `reports/agent_jobs/chat_evidence_actionability_and_csl_guard_v1_20260524/README.md`
- `reports/agent_jobs/cockpit_ui_wait_then_actionability_rollout_v1_20260524/README.md`
- `reports/agent_jobs/runtime_topology_reconciliation_impl_v1_20260524/README.md`
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/backend/app/routes/chat.py`
- `financial-engine_v2/backend/app/services/cockpit_service.py`
- `financial-engine_v2/backend/app/services/query_orchestrator.py`
- `financial-engine_v2/backend/app/services/tenn_chat.py`
- `financial-engine_v2/cockpit/core/chat.py`
- `cockpit-ui/lib/cockpit-chat-actionability.ts`
- `cockpit-ui/components/cockpit/chat/chat-screen.tsx`
- `cockpit-ui/lib/cockpit-types.ts`
- backend chat/source/query tests listed in validation.

## Final Template

Files changed:
- See "Files Changed".

Files inspected:
- See "Files Inspected".

Lane:
- Query Orchestration

Execution mode:
- AUDIT-FIRST SAFE EXTENSION

Collision risk:
- MEDIUM-HIGH, mitigated by isolated worktree and exact file allowlist.

Validation run:
- See "Validation".

Validation result:
- Focused backend helper/route/source-builder validation passed. One broader query-orchestrator baseline test failed unrelated and reproduced outside this worktree.

Files intentionally not touched:
- Retrieval ranking, QueryOrchestrator sufficiency logic, ChatController prompt/synthesis, source stores, Qdrant, news, memory, extraction, parser routing, runtime topology, Docker, systemd, cron, model/GPU config, frontend UI.

Remaining blockers:
- Exact historic CSL payload remains unavailable.
- Broader query-orchestrator sufficiency failure remains a separate pre-existing issue.

Next safe step:
- Add a follow-up QueryOrchestration/Evaluation task for the pre-existing QueryOrchestrator `sufficient_for_analysis` regression if that behavior is still desired.

Project Memory save recommendation:
- Save that backend Cockpit chat now has a deterministic evidence requirement helper integrated into response metadata, converting unsupported price/technical and metric claims into `market_data_missing` / `metric_extraction_missing` metadata before the UI receives the response.
