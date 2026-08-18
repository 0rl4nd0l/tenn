---
job_id: cockpit_chat_answer_readiness_contract_v1_20260604
lane: Query Orchestration
supporting_lanes:
  - Provenance
  - Evaluation
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_chat_answer_readiness_contract_v1_20260604.md
  - reports/agent_jobs/cockpit_chat_answer_readiness_contract_v1_20260604/README.md
  - reports/agent_jobs/cockpit_chat_answer_readiness_contract_v1_20260604/status.json
  - reports/agent_jobs/cockpit_chat_answer_readiness_contract_v1_20260604/validation.json
  - reports/agent_jobs/cockpit_chat_answer_readiness_contract_v1_20260604/api_probe_results.json
  - reports/agent_jobs/cockpit_chat_answer_readiness_contract_v1_20260604/browser_probe_results.json
  - reports/agent_jobs/cockpit_chat_answer_readiness_contract_v1_20260604/architecture_review.md
  - reports/agent_jobs/cockpit_chat_answer_readiness_contract_v1_20260604/diff-check.json
  - financial-engine_v2/backend/app/routes/cockpit_api.py
  - financial-engine_v2/backend/app/services/chat_readiness.py
  - financial-engine_v2/backend/tests/test_cockpit_chat_readiness.py
  - cockpit-ui/app/api/cockpit/chat/readiness/route.ts
  - cockpit-ui/components/cockpit/chat/chat-screen.tsx
  - cockpit-ui/components/cockpit/chat/chat-screen.test.tsx
  - cockpit-ui/components/cockpit/chat/terminal-message.tsx
  - cockpit-ui/components/cockpit/chat/terminal-message.test.tsx
  - cockpit-ui/lib/api-client.ts
  - cockpit-ui/lib/cockpit-chat-readiness.ts
  - cockpit-ui/lib/cockpit-chat-readiness.test.ts
  - cockpit-ui/lib/cockpit-types.ts
  - cockpit-ui/tests/chat-readiness.spec.ts
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 21600
output_dir: reports/agent_jobs/cockpit_chat_answer_readiness_contract_v1_20260604
mutation_mode: safe_extension
production_data_access: false
---

# Cockpit Chat Answer Readiness Contract

## Objective

Build a capability-scoped answer readiness contract for Cockpit chat so `/full-chat`
does not invite normal financial analysis when the required local/dev evidence
stack is unavailable. The UI must either show verified/source-labeled readiness
or precise blockers and safe local activation actions.

## Required Capability Scope

- financial_fact
- filing/document summary
- local_news/RAG
- portfolio/holdings context
- memory_context
- strategy/action_preview
- model route/runtime

## Allowed Implementation

- Add a read-only backend readiness helper and Cockpit route that reports
  capability status, blockers, safe local/dev activation hints, and route-level
  evidence without probing or mutating production/canonical stores.
- Update `/full-chat` to consume readiness and gate normal analysis affordances
  when the relevant capability is not ready.
- Harden frontend response presentation so `DATA_MISSING` and unverified numeric
  claims are not displayed as normal verified facts.
- Add focused backend and frontend tests for the readiness contract, UI gating,
  and `DATA_MISSING` rendering behavior.
- Record API/browser probe evidence in the report bundle.

## Forbidden

- No deploys, trades, external production service changes, order placement, or
  production/canonical writes.
- No broad backfills, index rebuilds, projection repair, extraction runs, or
  store canonicalization.
- No DB, Qdrant, vector, embedding, news, memory, or financial-truth writes.
- No embedding backend changes, fallback embedding logic, vector metric changes,
  vector ID changes, or direct frontend retrieval authority.
- No source-label weakening, no promotion of `context_only`, `memory_context`,
  `financial_truth_numeric`, or unverified numeric context to `claim_verified`.
- No unrelated UI redesign or absorption of dirty state from other worktrees.

## Validation

- Validate this task card.
- Run registry list/overlap checks and claim only if safe.
- Reproduce the baseline with read-only API probes and browser evidence for
  BHP, CSL, MIN, A2M, and a no-hit control.
- Run focused backend tests for the readiness route/helper and chat metadata.
- Run focused frontend tests for readiness presentation and `/full-chat` gating.
- Run `git diff --check`.
- Run task-card `check-diff`.
- Verify `/full-chat` with Playwright screenshots and console/network/page-error
  capture across desktop and mobile where practical.
