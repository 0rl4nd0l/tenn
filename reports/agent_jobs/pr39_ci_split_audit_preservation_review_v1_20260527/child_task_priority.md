# PR #39 Child Task Priority

No child task cards or GitHub issues were created by this review.

## 1. C01 - Architecture Invariant Reconciliation

Lane: Evaluation, with Repo Hygiene support.

Recommended title: `[CI] Reconcile backend sqlite3/uuid4/vector invariant failures for PR #39`

Why priority: highest merge-confidence risk; policy mismatch around runtime
`sqlite3`, random `uuid4`, and vector IDs can invalidate broad backend safety
assumptions before smaller CI fixes matter.

Blocked by: architecture ownership decision if existing SQLite-backed
memory/operational stores intentionally conflict with the invariant.

Forbidden surfaces: production DB/Qdrant/news/memory, canonical financial truth,
parser routing, extraction prompts, gold labels, runtime/model/GPU/service
config, invariant relaxation without explicit migration approval.

Validation: focused architecture invariant and cursor-rule pytest, Ruff on
changed files, architecture-check against current architecture docs.

## 2. C02 - Cockpit Chat Controller Contract

Lane: Query Orchestration.

Recommended title: `[CI] Align Cockpit chat controller test doubles with llm_client contract`

Why priority: high failure count and close to chat/session behavior; likely
blocks useful PR reruns even if architecture issues are resolved.

Blocked by: deciding whether tests or service constructor contract owns the
`llm_client` parameter.

Forbidden surfaces: runtime/model/GPU/service config, broad router rewrites,
test-only masking without proving `chat_stream` behavior.

Validation: focused cockpit service session/thread and conversation continuity
pytest.

## 3. C03 - Cockpit Subagent Event Loop

Lane: Query Orchestration.

Recommended title: `[CI] Make Cockpit subagent event-loop contract explicit under pytest-asyncio`

Why priority: high failure count and related to Cockpit subagent stability.

Blocked by: deciding whether event-loop creation belongs in test harness or
subagent runtime boundary.

Forbidden surfaces: live local LLM, memory store mutation, runtime/model/GPU
service config, broad async framework rewrite.

Validation: focused `financial-engine_v2/cockpit/tests/test_subagents.py`.

## 4. C04 - Streaming Subprocess job_id Contract

Lane: Repo Hygiene.

Recommended title: `[CI] Align streaming subprocess helper tests with required job_id`

Why priority: small and contract-shaped; can reduce CI noise before broader
Cockpit reruns.

Blocked by: confirming required `job_id` is intended API, not an accidental
test break.

Forbidden surfaces: live subprocess action execution outside tests,
runtime/service config, broad action framework rewrite.

Validation: focused `financial-engine_v2/backend/tests/test_streaming_subprocess.py`.

## 5. C05 - News Loader Ollama URL API

Lane: Query Orchestration.

Recommended title: `[CI] Verify or carry Ollama URL loader repair into PR #39 before rerun`

Why priority: known API drift with a local post-PR-head candidate repair; should
be verified before rerunning PR #39.

Blocked by: PR #39 head not containing local later commits; no PR update is
approved in this task.

Forbidden surfaces: production news store, Qdrant mutation, live nightly sync,
runtime/model/GPU/service config.

Validation: focused `financial-engine_v2/backend/tests/test_load_news_to_qdrant.py`
with static proof that no live sync/backfill ran.

## 6. C08 - Hybrid Router Policy Contract

Lane: Query Orchestration.

Recommended title: `[CI] Decide HybridRouter force-local and on_chunk wrapper contract`

Why priority: product-risk cluster affecting routing policy and streaming
callback behavior.

Blocked by: explicit decision on force-local/API-vs-local behavior and stream
callback wrapper contract.

Forbidden surfaces: runtime/model/GPU/service config, silent fallback routing,
policy changes without explicit contract.

Validation: focused `financial-engine_v2/cockpit/tests/test_router_edge_cases.py`.

## 7. C07 - Cockpit Grounding Stress Expectations

Lane: Query Orchestration.

Recommended title: `[CI] Reconcile Cockpit stress expectations with grounded refusal and action-preview behavior`

Why priority: high-risk because stale tests may encode unsafe financial-answer
behavior, while real regressions would affect user-facing Cockpit behavior.

Blocked by: deciding intended grounded refusal/action-preview semantics after
recent guard changes.

Forbidden surfaces: financial truth loosening, grounding guard removal, live
tool execution, runtime/model/GPU/service config.

Validation: focused Cockpit agent stress and chat-change pytest.

## 8. C09 - Memo Signal Routing

Lane: Memory.

Recommended title: `[CI] Restore or re-contract memo extractor signal routing in isolated tests`

Why priority: product-risk memory signal loss can silently degrade company-memory
behavior.

Blocked by: isolated proof of whether current routing should write signals or
tests are stale.

Forbidden surfaces: production memory stores, production news stores, canonical
financial truth, broad memory migration.

Validation: focused memo extractor signal-routing pytest using isolated temp
stores only.

## 9. C13 - Query Sufficiency Guard

Lane: Query Orchestration.

Recommended title: `[CI] Restore query sufficiency guard when only announcement/news context is available`

Why priority: product-risk sufficiency honesty issue; should not be hidden by
fixture-only fixes.

Blocked by: DATA_MISSING on exact root cause without a focused child validation
run.

Forbidden surfaces: canonical financial truth, parser routing, source-label
relaxation, production data mutation.

Validation: focused `financial-engine_v2/backend/tests/test_query_orchestrator.py`.

## 10. C11 - Real-Gold PDF Asset

Lane: Evaluation.

Recommended title: `[CI] Resolve missing real-gold PDF asset path or fixture contract for PR #39`

Why priority: deterministic asset blocker that can keep CI red after code fixes.

Blocked by: asset provenance/path decision; no gold-label mutation is authorized.

Forbidden surfaces: gold label mutation without provenance review, parser
routing, extraction prompts, canonical financial truth.

Validation: focused extraction gold eval pytest and asset provenance check before
adding or relocating any PDF.

## 11. C12 - Process Document Redis/Celery CI Dependency

Lane: Repo Hygiene.

Recommended title: `[CI] Isolate process-document API test from live Redis or declare CI Redis service`

Why priority: CI environment dependency should be made explicit before declaring
PR health.

Blocked by: decision between test isolation and CI service declaration.

Forbidden surfaces: production Redis/Celery, production DB, Qdrant, runtime
service config outside CI/test contract.

Validation: focused process-document API pytest and read-only workflow review;
no live worker run.

## 12. C06 - Marketplace Time-Stable Fixtures

Lane: Evaluation.

Recommended title: `[CI] Stabilize marketplace benchmark fixtures against wall-clock drift`

Why priority: inherited fixture drift can keep CI red after higher-risk product
and architecture clusters are addressed.

Blocked by: deciding whether the failing expectations represent stale
time-sensitive fixtures or real marketplace behavior.

Forbidden surfaces: production marketplace data, canonical financial truth,
expectation relaxation that hides stale benchmark behavior.

Validation: focused marketplace price intelligence, scanner, and API pytest.

## 13. C10 - Cockpit Preferences Runtime Target Contract

Lane: Query Orchestration.

Recommended title: `[CI] Settle Cockpit preferences chat_runtime_target API contract`

Why priority: smallest DATA_MISSING API-shape cluster; useful after the higher
blast-radius router/query clusters are settled.

Blocked by: deciding whether `chat_runtime_target` is an intended response
field or stale expectation drift.

Forbidden surfaces: runtime/model/GPU/service config, frontend behavior change
without API contract update.

Validation: focused `financial-engine_v2/backend/tests/test_cockpit_api_preferences.py`.
