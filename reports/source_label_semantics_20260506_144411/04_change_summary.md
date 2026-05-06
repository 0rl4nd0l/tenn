# Change Summary

## Backend Chat Metadata

`financial-engine_v2/backend/app/services/tenn_chat.py`

- Added conservative evidence label helpers for source rows.
- Added local ticker-news expectation tracking without changing retrieval ranking.
- Added answer-level `evidence_labels`, `source_coverage_status`, and `evidence_status`.
- Added no-hit and missing-required-evidence metadata when local ticker-news is expected but absent.
- Added degraded runtime metadata for degraded Tenn chat payloads and failed news retrieval.

## Cockpit API Normalization

`financial-engine_v2/backend/app/routes/cockpit_api.py`

- Preserved the existing taxonomy surface.
- Made unknown source type fallback safer by prioritizing `unknown_unclassified` over `context_only`.
- Made financial truth coverage explicit when financial truth labels are present.

## Agent Loop

`financial-engine_v2/cockpit/core/agent_loop.py`

- Added degraded runtime routing metadata for synthesis timeout with evidence.
- Added degraded runtime routing metadata for LLM call failure.

## UI Metadata and Rendering

`cockpit-ui/lib/cockpit-types.ts`

- Added evidence/source label fields to analyst metadata and source types.

`cockpit-ui/lib/api-client.ts`

- Maps backend source label fields into UI source objects.

`cockpit-ui/components/cockpit/chat/chat-screen.tsx`

- Preserves answer-level evidence label metadata and per-source labels from API and SSE payloads.

`cockpit-ui/components/cockpit/chat/terminal-message.tsx`

- Replaces the generic source-backed trust label on updated paths with role-aware labels.
- Shows per-source compact labels in the terminal source list.

## Tests

Focused tests now cover:

- A2M local news claim support and context-only fallback.
- Expected ticker-news no-hit/missing evidence.
- No-hit source normalization.
- Runtime degraded metadata.
- Holdings local personal data boundary.
- Memory context non-verification.
- External web context non-canonical boundary.
- Unknown source type safe fallback.
- UI trust label rendering for claim-supported and no-hit cases.

## Source Drawer

The source drawer was inspected but not changed. This keeps the implementation small and avoids redesigning the UI. Backend and UI source models now carry enough metadata for a later source drawer display update.
