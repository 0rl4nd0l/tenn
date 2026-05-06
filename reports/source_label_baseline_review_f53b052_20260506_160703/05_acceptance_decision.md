# Acceptance Decision

Decision: `ACCEPT_BASELINE`

## Why Accepted

- Source labels are persisted for delivered assistant turns.
- Reload returns saved source rows and routing metadata.
- Frontend hydration preserves `evidenceLabel`, `evidenceLabels`, `claimVerified`, and source coverage metadata.
- Visible chat source rendering no longer labels all source-bearing answers as source-backed financial facts.
- Focused backend, cockpit, frontend typecheck, Vitest, ESLint, Ruff, and whitespace validation passed.
- No news/Qdrant, memory, extraction, financial truth, Holdings, Marketplace, Watchlist, Commentary route parity, or chat learning scorer files were changed by this audit.

## What It Fixes

- Current-turn source labels survive session reload.
- Attached-source evidence is visible as `context_only`, not `claim_verified`.
- Legacy rows without metadata fail safe as `unknown_unclassified`.
- Generic source-backed wording is replaced by role-specific wording.

## What It Does Not Fix

- Full Source Label Semantics v1.
- Non-news no-hit operational paths.
- Deep/web runtime degradation consistency across all answer paths.
- QueryOrchestrator direct consumers that bypass Cockpit API inference.
- Legacy `/api/chat` taxonomy envelopes.
- Textual `/sources list` role rendering.
- Fine-grained financial document/announcement span precision.

Source Label Semantics v1 remains needed.
