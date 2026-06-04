---
job_id: chat_answer_presentation_model_v1_20260604
lane: Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/chat_answer_presentation_model_v1_20260604.md
  - reports/agent_jobs/chat_answer_presentation_model_v1_20260604/README.md
  - reports/agent_jobs/chat_answer_presentation_model_v1_20260604/status.json
  - reports/agent_jobs/chat_answer_presentation_model_v1_20260604/validation.json
  - reports/agent_jobs/chat_answer_presentation_model_v1_20260604/diff-check.json
  - cockpit-ui/lib/cockpit-chat-presentation.ts
  - cockpit-ui/lib/cockpit-chat-presentation.test.ts
  - cockpit-ui/components/cockpit/chat/terminal-message.tsx
  - cockpit-ui/components/cockpit/chat/terminal-message.test.tsx
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 21600
output_dir: reports/agent_jobs/chat_answer_presentation_model_v1_20260604
mutation_mode: safe_extension
production_data_access: false
---

# Chat Answer Presentation Model

## Objective

Move answer type, trust label, blockers, evidence summary, suggested next
actions, and action-preview presentation state out of `TerminalMessage` and
behind a frontend presentation model.

## Allowed Implementation

- Add a pure frontend presentation model module for assistant-message analyst
  shell state and action-preview state.
- Keep `TerminalMessage` as the markup adapter that renders the model and wires
  component-local callbacks such as opening sources.
- Add focused unit tests for the presentation model and preserve existing
  `TerminalMessage` behavior.

## Forbidden

- No backend, DB, Qdrant, memory-store, financial truth data, runtime-service,
  embedding, extraction, ingestion, schema, or vector changes.
- No browser harness, Playwright fixture, or `MultipassResult` contract work in
  this slice.
- No visual redesign beyond preserving the existing rendered behavior.
- No cleanup or absorption of unrelated worktree dirt from other checkouts.

## Validation

- Validate this task card.
- Check and claim the shared registry before implementation.
- Run focused frontend presentation and `TerminalMessage` tests.
- Run frontend TypeScript for the touched surface.
- Run `git diff --check`.
- Run `check-diff` before closeout.
