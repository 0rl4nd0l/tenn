# Chat Evidence Taxonomy Deepening

## Scope

- Worktree: `/home/l4nd0/tenn-chat-evidence-taxonomy-deep-v1-20260604`
- Branch: `safe/chat-evidence-taxonomy-deep-v1-20260604`
- Lane: Query Orchestration
- Mode: safe extension

## Result

Implemented the first architecture slice: deep evidence-label taxonomy semantics.
The shared taxonomy now owns context-only boundaries, effective claim
verification, canonical financial-truth eligibility, and coverage priority.

Memory and context-only evidence now stay qualitative/context-only even when raw
payloads include `claim_verified`, `financial_truth`, or
`financial_truth_numeric`.

## Touched Surfaces

- Backend shared taxonomy and consumers:
  - `financial-engine_v2/shared/evidence_labels.py`
  - `financial-engine_v2/backend/app/services/query_orchestrator.py`
  - `financial-engine_v2/backend/app/services/chat_evidence_guard.py`
  - `financial-engine_v2/backend/app/services/tenn_chat.py`
  - `financial-engine_v2/backend/app/routes/cockpit_api.py`
- Frontend presentation taxonomy:
  - `cockpit-ui/lib/cockpit-evidence-taxonomy.ts`
  - `cockpit-ui/lib/cockpit-chat-actionability.ts`
  - `cockpit-ui/components/cockpit/chat/terminal-message.tsx`

## Validation

- Backend focused bundle: 153 passed.
- Backend ruff on touched Python files: passed.
- Frontend TypeScript: passed.
- Frontend focused Vitest: 24 passed.

## Out Of Scope

- No DB, Qdrant, memory-store, runtime-service, financial-truth data,
  extraction, ingestion, embedding, schema, or vector changes.
- Browser regression harness and `MultipassResult` contract work were not part
  of this first slice.
