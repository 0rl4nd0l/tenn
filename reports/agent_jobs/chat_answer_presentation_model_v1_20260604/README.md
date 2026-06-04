# Chat Answer Presentation Model

Generated: 2026-06-04

## Scope

Implemented the third handoff slice: answer presentation state now lives behind
a frontend model instead of inside `TerminalMessage`.

## Changes

- Added `cockpit-ui/lib/cockpit-chat-presentation.ts`.
- Moved analyst shell derivation out of `TerminalMessage`, including answer
  type, trust label, blockers/gaps, evidence summary, source-state labels, and
  suggested next actions.
- Moved action-preview display state out of `TerminalMessage`, including risk
  labels, why text, impact text, parameter summary, and confirmation safety
  text.
- Kept `TerminalMessage` as the render adapter that wires local UI callbacks
  such as opening the source panel.
- Added presentation-model tests while preserving existing component render
  coverage.

## Guardrails

- No backend, DB, Qdrant, memory-store, financial truth data, runtime-service,
  embedding, extraction, ingestion, schema, or vector changes.
- No visual redesign; the component tests preserve the existing rendered labels
  and controls.
- Browser harness and `MultipassResult` work remain out of scope.

## Validation

- `pnpm --dir cockpit-ui exec vitest run lib/cockpit-chat-presentation.test.ts lib/cockpit-chat-actionability.test.ts components/cockpit/chat/terminal-message.test.tsx`
- `pnpm --dir cockpit-ui exec tsc --noEmit --pretty false --incremental false`
- `pnpm --dir cockpit-ui exec eslint lib/cockpit-chat-presentation.ts lib/cockpit-chat-presentation.test.ts components/cockpit/chat/terminal-message.tsx components/cockpit/chat/terminal-message.test.tsx`
- `git diff --check`
