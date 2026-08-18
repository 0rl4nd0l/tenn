---
job_id: strict_local_news_context_claim_verified_route_v1_20260526
lane: Query Orchestration
supporting_lanes:
  - Provenance
  - Evaluation
  - Reporting
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/strict_local_news_context_claim_verified_route_v1_20260526.md
  - reports/agent_jobs/strict_local_news_context_claim_verified_route_v1_20260526/README.md
  - reports/agent_jobs/strict_local_news_context_claim_verified_route_v1_20260526/status.json
  - reports/agent_jobs/strict_local_news_context_claim_verified_route_v1_20260526/validation_results.json
  - reports/agent_jobs/strict_local_news_context_claim_verified_route_v1_20260526/smoke_results.json
  - reports/agent_jobs/strict_local_news_context_claim_verified_route_v1_20260526/diff_review.md
  - reports/agent_jobs/strict_local_news_context_claim_verified_route_v1_20260526/diff-check.json
  - financial-engine_v2/cockpit/core/chat.py
  - financial-engine_v2/cockpit/tests/test_chat_ticker_detection.py
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py
  - financial-engine_v2/backend/tests/test_build_ui_sources.py
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 21600
output_dir: reports/agent_jobs/strict_local_news_context_claim_verified_route_v1_20260526
mutation_mode: safe_extension
requested_mutation_mode: implementation
production_data_access: false
---

# Strict Local News Context Claim-Verified Route

## Objective

Make prompts like `Use only local_news_context for BHP` route through the same
claim-verified local-news source-pack path as direct `news for BHP` requests,
while preserving guarded `DATA_MISSING` behavior when local news is absent or
only context-only/degraded evidence is available.

## System Layer

- Target layer: Query Orchestration.
- Supporting layers: Provenance, Evaluation, Reporting, Repo Hygiene.
- Relevant contract: backend owns retrieval and source-pack assembly; evidence
  gaps must remain explicit; Cockpit must not use direct DB/Qdrant access.

## Allowed Scope

- Route strict local-news-context ticker prompts into the existing local-news
  short-circuit/source-pack behavior.
- Preserve the existing claim-verification semantics for successful direct-news
  and tool-backed local-news hits.
- Add focused regression coverage for strict local-news-only prompts and
  no-local-news controls.
- Record validation and read-only smoke evidence in the report bundle.

## Forbidden

- DB, Qdrant, or news-store mutation.
- Reindex, resync, backfill, projection rebuild, or projection repair.
- Migrations.
- Parser routing changes.
- Canonical financial truth writes.
- Tenn memory writes, cleanup, or canonicalization.
- Runtime, model, GPU, Docker, systemd, cron, env, or volume config edits.
- Broad UI redesign.
- One-off ticker alias hardcoding.
- Weakening `chat_evidence_guard.py` or the landed local-news honesty guard.
- Allowing filings, documents, price context, memory, or web context to satisfy
  local-news claims.
- Hiding degraded runtime states.
- Relabelling context-only/no-hit/degraded evidence as verified.
- Relaxing tests to accept dishonest source-grounding.
- Cleaning, stashing, resetting, deleting, or committing unrelated files.

## Validation

- Validate this task card.
- Run registry list/overlap checks and claim only if safe.
- Run focused Python compile, Ruff, and pytest coverage for changed code/tests.
- Run existing local-news honesty/source-pack guard tests.
- Run `git diff --check`.
- Run task-card `check-diff`.
- If integration succeeds, run backend-only read-only live smoke without
  mutating data stores or restarting unrelated services.
