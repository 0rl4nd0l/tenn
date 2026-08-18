---
job_id: natural_language_local_news_intent_route_v1_20260526
lane: Query Orchestration
supporting_lanes:
  - Provenance
  - Evaluation
  - Reporting
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/natural_language_local_news_intent_route_v1_20260526.md
  - reports/agent_jobs/natural_language_local_news_intent_route_v1_20260526/README.md
  - reports/agent_jobs/natural_language_local_news_intent_route_v1_20260526/status.json
  - reports/agent_jobs/natural_language_local_news_intent_route_v1_20260526/pre_fix_intent_matrix.json
  - reports/agent_jobs/natural_language_local_news_intent_route_v1_20260526/root_cause_trace.json
  - reports/agent_jobs/natural_language_local_news_intent_route_v1_20260526/validation_results.json
  - reports/agent_jobs/natural_language_local_news_intent_route_v1_20260526/post_fix_intent_matrix.json
  - reports/agent_jobs/natural_language_local_news_intent_route_v1_20260526/smoke_results.json
  - reports/agent_jobs/natural_language_local_news_intent_route_v1_20260526/diff_review.md
  - reports/agent_jobs/natural_language_local_news_intent_route_v1_20260526/diff-check.json
  - financial-engine_v2/cockpit/core/chat.py
  - financial-engine_v2/cockpit/tests/test_chat_ticker_detection.py
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py
  - financial-engine_v2/backend/tests/test_build_ui_sources.py
  - financial-engine_v2/backend/tests/test_chat_evidence_guard.py
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 21600
output_dir: reports/agent_jobs/natural_language_local_news_intent_route_v1_20260526
mutation_mode: safe_extension
requested_mutation_mode: implementation
production_data_access: false
---

# Natural-Language Local-News Intent Route

## Objective

Make natural-language local-news prompts such as `latest local news for BHP`,
`what is the latest news on CSL`, and `recent local news for A2M` route through
the same claim-verified ticker-news source-pack path as direct `news for TICKER`
and strict `Use only local_news_context for TICKER` prompts.

## System Layer

- Target layer: Query Orchestration.
- Supporting layers: Provenance, Evaluation, Reporting, Repo Hygiene.
- Relevant contract: backend remains the authority for retrieval and source-pack
  assembly; Cockpit may orchestrate but must not perform independent retrieval
  pipelines; evidence gaps must remain explicit and source labels must remain
  honest.

## Allowed Scope

- Prove the current natural-language local-news routing behavior before code
  changes.
- Extend existing generic ticker/news intent routing only if the current branch
  does not already route natural-language prompts through the ticker-news path.
- Preserve direct `news for TICKER` and strict `local_news_context` behavior.
- Preserve `chat_evidence_guard.py` semantics and local-news honesty behavior.
- Add focused regression tests and report artifacts.
- Run read-only backend smoke after implementation/integration if needed to
  prove the backend serves the integrated code.

## Forbidden

- DB, Qdrant, or news-store mutation.
- Reindex, resync, backfill, projection rebuild, or projection repair.
- Migrations.
- Parser routing changes.
- Canonical financial truth writes.
- Tenn memory writes, cleanup, or canonicalization.
- Runtime, model, GPU, env, compose, volume, or broad service config edits.
- Broad UI redesign.
- One-off ticker alias hardcoding.
- Weakening `chat_evidence_guard.py` or local-news honesty behavior.
- Allowing filings, documents, price context, memory, or web context to satisfy
  local-news claims.
- Hiding degraded runtime or schema states.
- Relabelling context-only, no-hit, or degraded evidence as verified.
- Relaxing tests to accept dishonest source-grounding.
- Cleaning, stashing, resetting, deleting, or committing unrelated files.

## Validation

- Validate this task card.
- Run registry list/overlap checks and claim only if safe.
- Write pre-fix prompt matrix and root-cause trace before implementation.
- Run JSON validation for report artifacts.
- Run Python compile, Ruff, focused routing/source-pack tests, chat stream tests,
  build-ui-source tests, and chat evidence guard tests as applicable.
- Run `git diff --check`.
- Run task-card `check-diff`.
- Run an architecture review confirming no forbidden mutation or source-label
  masking.
