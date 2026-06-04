---
job_id: chat_evidence_taxonomy_deep_v1_20260604
lane: Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/chat_evidence_taxonomy_deep_v1_20260604.md
  - reports/agent_jobs/chat_evidence_taxonomy_deep_v1_20260604/README.md
  - reports/agent_jobs/chat_evidence_taxonomy_deep_v1_20260604/status.json
  - reports/agent_jobs/chat_evidence_taxonomy_deep_v1_20260604/validation.json
  - reports/agent_jobs/chat_evidence_taxonomy_deep_v1_20260604/diff-check.json
  - financial-engine_v2/shared/evidence_labels.py
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/app/services/evidence_taxonomy.py
  - financial-engine_v2/backend/app/services/query_orchestrator.py
  - financial-engine_v2/backend/app/services/chat_evidence_guard.py
  - financial-engine_v2/backend/app/services/tenn_chat.py
  - financial-engine_v2/backend/tests/test_evidence_label_semantics.py
  - financial-engine_v2/backend/tests/test_build_ui_sources.py
  - cockpit-ui/lib/cockpit-evidence-taxonomy.ts
  - cockpit-ui/lib/cockpit-chat-actionability.ts
  - cockpit-ui/lib/cockpit-chat-actionability.test.ts
  - cockpit-ui/components/cockpit/chat/terminal-message.tsx
  - cockpit-ui/components/cockpit/chat/terminal-message.test.tsx
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 21600
output_dir: reports/agent_jobs/chat_evidence_taxonomy_deep_v1_20260604
mutation_mode: safe_extension
production_data_access: false
---

# Chat Evidence Taxonomy Deepening

## Objective

Centralize chat evidence label semantics so `memory_context` and `context_only`
remain qualitative/context-only and cannot promote to `claim_verified` or
canonical financial truth.

## Allowed Implementation

- Add a backend evidence taxonomy helper for label normalization, ordering,
  context-only semantics, claim-verified eligibility, and coverage status.
- Move existing backend chat evidence consumers toward that helper without
  changing retrieval, DB, Qdrant, embeddings, extraction, or runtime services.
- Add focused backend regression tests proving context-only memory cannot count
  as verified canonical evidence.
- Add a frontend evidence taxonomy/presentation adapter and update chat
  actionability/TerminalMessage to consume that shared presentation semantics.

## Forbidden

- No DB, Qdrant, memory-store, financial truth data, runtime-service, embedding,
  extraction, ingestion, schema, or vector changes.
- No promotion of company, market, or user thesis memory into canonical numeric
  truth.
- No broad answer source-plan, browser harness, or `MultipassResult` contract
  work in this first slice.
- No cleanup or absorption of unrelated worktree dirt from other checkouts.

## Validation

- Validate this task card.
- Check and claim the shared registry before implementation.
- Run focused backend tests for evidence label semantics.
- Run focused frontend tests for actionability and TerminalMessage semantics.
- Run `git diff --check`.
- Run `check-diff` before closeout.
