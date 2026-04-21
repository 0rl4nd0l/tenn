# Cockpit Request Standards

This folder defines markdown-first standards for recurring Cockpit request types.

## Purpose

- Keep request behavior consistent across sessions and models.
- Make expected analysis structure explicit and reviewable.
- Provide a single reference location that runtime hooks can safely point to.

## Current Standards

- `company_analysis.md`
- `daily_market_update.md`
- `sector_analysis.md`
- `watchlist_triage.md`

## Enforcement Maturity

- Current runtime behavior is prompt-level guidance injection only.
- Structural output validation is not yet implemented.
- Standards improve consistency but do not guarantee strict compliance.

## Runtime Conformance Boundaries

- Prompt guidance is injected in the three LLM-backed chat paths:
  - keyword LLM fallback (`ChatController.build_chat_response`)
  - structured agent-loop path (`_run_agent_loop`)
  - orchestrated synthesis path (`_build_orchestrated_response`)
- Deterministic slash/control paths intentionally bypass prompt guidance.
  - Example: `/market-update ...` and conversational rewrites such as "today's market update" route to deterministic market-update handlers without an LLM synthesis prompt.
- This means daily market-update coverage is split:
  - deterministic command path: bounded non-LLM report rendering
  - narrative LLM path: request-standard prompt guidance when routed through LLM-backed chat

## Authoring Rules For New Standards

Use this structure so future standards remain comparable:

1. `Scope and Trigger`
2. `Inputs and Evidence Contract`
3. `Execution Steps`
4. `Output Contract`
5. `Memory and Follow-up Rules`

Keep standards additive and avoid redefining backend authority or retrieval ownership.
