---
job_id: ticker_news_source_grounding_system_fix_v1_20260525
lane: Query Orchestration
supporting_lanes:
  - Provenance
  - Evaluation
  - Reporting
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/ticker_news_source_grounding_system_fix_v1_20260525.md
  - reports/agent_jobs/ticker_news_source_grounding_system_fix_v1_20260525/README.md
  - reports/agent_jobs/ticker_news_source_grounding_system_fix_v1_20260525/status.json
  - reports/agent_jobs/ticker_news_source_grounding_system_fix_v1_20260525/blast_radius_matrix.json
  - reports/agent_jobs/ticker_news_source_grounding_system_fix_v1_20260525/root_cause_trace.json
  - reports/agent_jobs/ticker_news_source_grounding_system_fix_v1_20260525/validation_results.json
  - reports/agent_jobs/ticker_news_source_grounding_system_fix_v1_20260525/smoke_results.json
  - reports/agent_jobs/ticker_news_source_grounding_system_fix_v1_20260525/diff_review.md
  - financial-engine_v2/backend/app/services/chat_evidence_guard.py
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/tests/test_chat_evidence_guard.py
  - financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py
  - financial-engine_v2/backend/tests/test_sources.py
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
timeout_seconds: 21600
output_dir: reports/agent_jobs/ticker_news_source_grounding_system_fix_v1_20260525
mutation_mode: safe_extension
requested_mutation_mode: implementation
production_data_access: false
---

# Ticker News Source Grounding System Fix

Audit-first implementation task for the Cockpit ticker-universe news and
source-grounding regression class. A2M is the seed canary, not the full scope.
The repo task-card contract does not support literal `mutation_mode:
implementation`, so this card uses the closest valid repo-native mode,
`safe_extension`, while preserving the requested implementation intent in
`requested_mutation_mode`.

## Objective

Make local/news evidence retrieval, source classification, and final synthesis
honest across a representative ASX ticker basket. Land a systemic fix only if
the shared root cause is proven and multi-ticker regression tests pass.

## Allowed Files

The write surface is limited to this task card, the required report bundle, the
Cockpit chat evidence guard, the Cockpit chat route where the guard is applied,
and focused backend regression tests for those surfaces.

Ownership was confirmed from repo evidence:

- `financial-engine_v2/backend/app/services/chat_evidence_guard.py` owns
  response-level evidence requirement labels and visible evidence-gap wording.
- `financial-engine_v2/backend/app/routes/cockpit_api.py` owns Cockpit chat
  source presentation metadata and applies visible evidence guard text before
  response delivery.
- `financial-engine_v2/backend/tests/test_chat_evidence_guard.py`,
  `financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py`, and
  `financial-engine_v2/backend/tests/test_sources.py` cover source-label
  semantics, claim verification, degraded runtime, and Cockpit chat response
  contract behavior.

Potential implementation files may only come from these approved surfaces after
ownership is confirmed:

- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/backend/app/services/**`
- `financial-engine_v2/backend/tests/**`
- `financial-engine_v2/backend/app/**/news*.py` only if it owns Cockpit news retrieval/source assembly
- `financial-engine_v2/backend/app/**/source*.py` only if it owns source-label/source-coverage semantics
- `financial-engine_v2/backend/app/**/chat*.py` only if it owns prompt/source assembly for Cockpit chat
- `cockpit-ui/**` only if the proven root cause requires UI display of existing backend source states

## Forbidden

- DB mutation
- Qdrant mutation
- news-store mutation
- reindex, resync, backfill, projection rebuild, or projection repair
- parser routing changes
- canonical financial truth writes
- Tenn memory writes, cleanup, or canonicalization
- runtime, model, GPU, Docker, systemd, cron, or env config edits
- broad UI redesign
- one-off A2M alias hardcoding
- hiding degraded runtime states
- changing tests to accept dishonest source-grounding
- cleaning, stashing, resetting, deleting, or committing unrelated files
- committing foreign task cards unless separately authorized

## Required Preflight

1. Record branch, HEAD, worktree, `git status --short --untracked-files=all`,
   `git worktree list`, recent commits, registry/list-active,
   registry/check-overlap, and task-card validation.
2. Confirm the route-contract commit
   `c8d605e3de625c9f456edc0f3896b571a68f6b25` is an ancestor of the current
   HEAD or report if superseded.
3. Classify unrelated dirty/untracked task cards without touching them.
4. Claim the registry only if safe.
5. Confirm current backend route status for `/api/cockpit/news/status`,
   `/api/cockpit/config`, and relevant `/openapi.json` Cockpit paths when local
   services are safely available.
6. Read the existing A2M/status-route report bundles if present.

## Phase 1 - Blast Radius

Build a representative ASX ticker basket from locally available evidence. Include
A2M and at least four additional tickers if local evidence exists, plus one
low/no-local-news control if available. Write
`reports/agent_jobs/ticker_news_source_grounding_system_fix_v1_20260525/blast_radius_matrix.json`.

For each ticker, record local news presence, Qdrant evidence, news.sqlite
evidence, direct ticker/article evidence, alias/entity correctness, retrieval
and ranking behavior, local_news_context source presence, source coverage,
claim-verified counts, evidence labels, synthesis alignment, document/filing
misattribution, freshness/status honesty, degraded runtime/schema state, and a
classification from the requested taxonomy.

## Phase 2 - Root Cause

Identify the shared root cause before implementation. Stop with a blocking
report if storage is missing for most tickers, the fix requires forbidden
mutation, or root cause remains `DATA_MISSING`.

## Phase 3 - Systemic Fix

Allowed implementation patterns depend on the proven root cause: local-news
source guard, source-pack separation, generic ticker/company alias handling,
retrieval/ranking correction, or degraded-runtime honesty. Do not ship an A2M
patch, label masking, or prompt change that hides missing evidence.

## Phase 4 - Tests

Add focused regression tests proving A2M cannot answer local-news-only queries
from document/filing context, at least one other local-news ticker behaves
correctly, no-local-news controls do not fabricate local news, context-only
sources do not become claim-verified, source coverage and claim counts remain
honest, degraded runtime/schema state is surfaced, and news status route
contract tests still pass.

## Phase 5 - Read-Only Smoke

If tests pass and local services are safely available, run read-only route/chat
smokes with 30s stateless chat timeouts. Do not restart services unless the
reason is exact and separately approved by this card's boundaries.

## Phase 6 - Integration Or Parking

Integrate only if validation passes, the registry is conflict-free, and changed
files remain inside allowed files. If integration is blocked by active overlap,
dirty foreign work, branch drift, or missing merge-parking surfaces, freeze the
branch and write a report-local parking recommendation.

## Required Report Bundle

- `README.md`
- `status.json`
- `blast_radius_matrix.json`
- `root_cause_trace.json`
- `validation_results.json`
- `smoke_results.json` if live smoke is run
- `diff_review.md`

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/ticker_news_source_grounding_system_fix_v1_20260525.md`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/ticker_news_source_grounding_system_fix_v1_20260525.md`
- JSON validation for report artifacts
- `python3 -m py_compile` for changed backend Python files
- Ruff for changed backend Python files
- focused pytest for new/updated tests
- existing `financial-engine_v2/backend/tests/test_cockpit_news_status.py`
- route parity/source-label tests if present
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/ticker_news_source_grounding_system_fix_v1_20260525.md --no-write-report`
- architecture review for forbidden mutation and evidence-bound behavior

## Definition Of Done

Done means one of:

- FIX LANDED: systemic shared fix implemented, multi-ticker tests pass, A2M no
  longer misattributes document/filing context as local news, at least two
  non-A2M checks pass or are honestly classified, weak/degraded evidence remains
  labelled honestly, no forbidden mutation occurred, and report bundle is
  complete.
- BLOCKED WITH PROOF: blast radius and root cause are classified, required fix
  needs forbidden mutation or separate approval, no unsafe patch was made, and a
  precise next task is provided.
- PARKED: work is complete and validated but cannot be integrated, branch is
  frozen, parking metadata exists, and next merge-review path is explicit.
