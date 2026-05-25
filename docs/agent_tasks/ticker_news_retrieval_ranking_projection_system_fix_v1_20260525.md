---
job_id: ticker_news_retrieval_ranking_projection_system_fix_v1_20260525
lane: Query Orchestration
supporting_lanes:
  - Provenance
  - Evaluation
  - Reporting
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/ticker_news_retrieval_ranking_projection_system_fix_v1_20260525.md
  - reports/agent_jobs/ticker_news_retrieval_ranking_projection_system_fix_v1_20260525/README.md
  - reports/agent_jobs/ticker_news_retrieval_ranking_projection_system_fix_v1_20260525/status.json
  - reports/agent_jobs/ticker_news_retrieval_ranking_projection_system_fix_v1_20260525/pre_fix_ticker_matrix.json
  - reports/agent_jobs/ticker_news_retrieval_ranking_projection_system_fix_v1_20260525/news_path_map.md
  - reports/agent_jobs/ticker_news_retrieval_ranking_projection_system_fix_v1_20260525/root_cause_trace.json
  - reports/agent_jobs/ticker_news_retrieval_ranking_projection_system_fix_v1_20260525/validation_results.json
  - reports/agent_jobs/ticker_news_retrieval_ranking_projection_system_fix_v1_20260525/post_fix_ticker_matrix.json
  - reports/agent_jobs/ticker_news_retrieval_ranking_projection_system_fix_v1_20260525/post_fix_smoke_results.json
  - reports/agent_jobs/ticker_news_retrieval_ranking_projection_system_fix_v1_20260525/diff_review.md
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/app/services/rag.py
  - financial-engine_v2/backend/app/services/chat_evidence_guard.py
  - financial-engine_v2/backend/app/services/news_health_status.py
  - financial-engine_v2/backend/tests/test_build_ui_sources.py
  - financial-engine_v2/backend/tests/test_chat_evidence_guard.py
  - financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py
  - financial-engine_v2/backend/tests/test_cockpit_news_status.py
  - financial-engine_v2/backend/tests/test_rag_news_query.py
  - financial-engine_v2/backend/tests/test_sources.py
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 21600
output_dir: reports/agent_jobs/ticker_news_retrieval_ranking_projection_system_fix_v1_20260525
mutation_mode: safe_extension
requested_mutation_mode: implementation
production_data_access: false
---

# Ticker News Retrieval Ranking Projection System Fix

Audit-first implementation task for the remaining broad Cockpit ticker-news
retrieval, ranking, projection, and chat handoff regression after the local-news
source-grounding honesty guard landed. A2M is one canary only; this is a shared
ticker-universe system fix.

The repo task-card contract does not accept literal `mutation_mode:
implementation`; this card uses the closest valid repo-native mode,
`safe_extension`, while preserving the requested implementation intent in
`requested_mutation_mode`.

## Objective

Make locally available ASX company news discoverable, ranked ahead of
documents/filings for news-intent queries, preserved as `local_news_context`,
and handed into Cockpit chat synthesis across a representative ticker basket,
without weakening the local-news-only honesty guard.

## Required Scope

Primary lane: Query Orchestration.

Supporting lanes:

- Provenance
- Evaluation
- Reporting
- Repo Hygiene

Allowed implementation files must remain narrow and evidence-owned. The initial
candidate write surface is limited to the listed route, service, and focused
backend test files. Do not touch Cockpit UI unless root cause proves the backend
already returns correct source states and only frontend display is wrong.

## Forbidden

- DB mutation
- Qdrant mutation
- news-store mutation
- reindex, resync, backfill, projection rebuild, projection repair, or
  migrations
- parser routing changes
- canonical financial truth writes
- Tenn memory writes, cleanup, or canonicalization
- runtime, model, GPU, Docker, systemd, cron, or env config edits
- broad UI redesign
- one-off ticker alias hardcoding
- weakening the landed local-news honesty guard
- allowing filings/documents/price context to satisfy local-news claims
- hiding degraded runtime states
- relabelling `context_only`, no-hit, or degraded evidence as verified
- changing tests to accept dishonest source-grounding
- cleaning, stashing, resetting, deleting, or committing unrelated files
- committing foreign task cards unless separately authorized

## Required Preflight

1. Record `pwd`, branch, HEAD, worktree path, `git status
   --short --untracked-files=all`, `git worktree list`, and recent commits.
2. Confirm current HEAD contains
   `173a8750caa4602e5791ee072673db17e708c5d3` or a descendant with the same
   source-grounding fix, and inspect `chat_evidence_guard.py` plus Cockpit chat
   route integration.
3. Run registry/list-active and registry/check-overlap for this card. Claim the
   registry only if supported and safe.
4. Classify known unrelated task cards without editing them:
   `docs/agent_tasks/a2m_backend_reload_news_status_activation_smoke_v1_20260525.md`
   and
   `docs/agent_tasks/automation_audit_issue_preservation_v1_20260525.md`.
5. Validate this task card before implementation.
6. Confirm current runtime/status surfaces if services are running:
   `/api/cockpit/news/status`, `/api/cockpit/config`, and relevant Cockpit
   `/openapi.json` paths. Record whether `cockpit_announcement_context`
   missing-table warnings still appear.
7. Read the existing related report bundles if present.

## Phase 1 - Ticker-Universe Evidence Matrix

Choose a representative ASX ticker basket from locally available evidence, not
assumptions. Include A2M as a seed/canary, at least five additional ASX tickers
if local evidence exists, BHP, CSL, an ambiguity-heavy ticker such as WTC or
XRO, a previous failure such as COH or NST if evidence exists, and one
low/no-local-news control.

Write `pre_fix_ticker_matrix.json` with, for each ticker, company identity,
aliases, local storage state, Qdrant state, news.sqlite state, direct
ticker/article route evidence, status route truth, retrieval outside chat,
retrieval inside chat context assembly, news-intent ranking, source labels,
`local_news_context`, `source_coverage_status`,
`claim_verified_source_count`, synthesis alignment, freshness/status honesty,
runtime degradation, and classification from the requested taxonomy.

## Phase 2 - Hybrid News Path Map

Trace the Cockpit news path end to end: news/status route, direct ticker
news/article routes, Qdrant news retrieval, news.sqlite access, canonical local
news projection, entity resolution, filters/freshness, ranking/scoring, source
pack creation, chat source assembly, handoff to `chat_evidence_guard`, and
SSE/non-stream differences.

Write `news_path_map.md` and identify the first failing stage for each ticker.

## Phase 3 - Root-Cause Decision

Before editing implementation code, write `root_cause_trace.json` and choose
one of the allowed root-cause classes:

1. Generic ticker/company alias resolution failure.
2. News retrieval path bypassed or not called for news-intent chat.
3. Qdrant/news.sqlite/direct ticker-news parity gap.
4. Ranking lets documents/filings dominate news-intent context despite
   available local news.
5. Projection/status route reports availability incorrectly.
6. Source pack assembly drops or misclassifies retrieved local news.
7. Runtime/schema degradation materially affects context retrieval.
8. DATA_MISSING / no safe implementation without store mutation or reindex.

Stop if root cause is unclear, requires forbidden mutation, is an A2M-only
alias patch, or would weaken the honesty guard.

## Phase 4 - Systemic Fix

Allowed implementation patterns, only after root cause is proven:

- Generic news-intent retrieval handoff.
- Retrieval/ranking fix that prefers relevant `local_news_context` for
  news-intent queries while keeping no-hit controls guarded.
- Generic entity resolution using existing local metadata, not hardcoded aliases.
- Source pack assembly preserving local news separately from documents, filings,
  market data, memory, degraded, and no-hit context.
- Status/projection honesty correction that reports missing projection or
  degraded runtime honestly without repair/rebuild.
- Runtime/schema degraded reporting that surfaces `degraded_runtime` or
  `DATA_MISSING` without migrations.

## Phase 5 - Tests

Add or update focused regression tests proving available local news retrieval
for at least two non-A2M tickers or fixture equivalents, A2M remains guarded,
one no-local-news control is honest, documents/filings/price context cannot
satisfy local-news-only queries, `context_only` stays unverified,
`claim_verified_source_count` and `source_coverage_status` remain honest,
news-intent ranking prefers local news when present, source pack assembly keeps
`local_news_context` separate, status reports storage/projection/degraded states
honestly, SSE/non-stream behavior stays consistent, and existing route parity
and news status tests pass.

## Phase 6 - Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/ticker_news_retrieval_ranking_projection_system_fix_v1_20260525.md`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/ticker_news_retrieval_ranking_projection_system_fix_v1_20260525.md`
- JSON validation for report artifacts
- `python3 -m py_compile` for changed backend Python files
- Ruff for changed backend Python files
- focused pytest for changed/new tests
- existing source-grounding guard tests
- existing Cockpit news status tests
- route parity/source-label tests if present
- expanded status/source/route suite if affordable
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/ticker_news_retrieval_ranking_projection_system_fix_v1_20260525.md --no-write-report`
- architecture review for forbidden mutation, source-label masking, runtime
  config edits, one-off hardcoding, and honesty-guard weakening

## Phase 7 - Live Read-Only Smoke

If tests pass and local services are safely available, determine whether the
backend is serving changed code. Do not restart backend unless separately
approved by this card and current operator instruction. Do not restart Qdrant,
Postgres, workers, GPU worker, llama-server, Next, or unrelated services.

Run read-only stateless 30s probes for A2M, at least two non-A2M tickers with
local evidence, one no-local-news/control ticker, and one SSE smoke if safe.
Write `post_fix_smoke_results.json`.

## Phase 8 - Integration Or Parking

Integrate only if implementation is clean, validation passes, registry has no
conflicts, and changed files stay inside allowed files. If integration is
blocked, do not force it; freeze the branch and write report-local parking
metadata with branch, base, HEAD, changed files, validation, risks, and next
merge-review command.

## Required Report Bundle

- `README.md`
- `status.json`
- `pre_fix_ticker_matrix.json`
- `news_path_map.md`
- `root_cause_trace.json`
- `validation_results.json`
- `post_fix_ticker_matrix.json` if implementation occurs
- `post_fix_smoke_results.json` if live smoke runs
- `diff_review.md`

## Definition Of Done

Done means one of:

- FIX LANDED: broad root cause is proven, a systemic code-only fix is
  implemented, tests pass across A2M and multiple non-A2M tickers or fixtures,
  available local news is retrieved/ranked/handed to chat where present,
  no-news/projection-missing cases remain honestly `DATA_MISSING` or degraded,
  the source-grounding guard remains intact, no forbidden mutation occurred, and
  the final report is complete.
- BLOCKED WITH PROOF: root cause requires store mutation, migration,
  reindex/resync, projection rebuild/repair, or runtime/config work outside this
  task, no unsafe patch was made, and the exact next task is written.
- PARKED: work is complete and validated but cannot be integrated, branch is
  frozen, parking metadata exists, and next merge-review path is explicit.
