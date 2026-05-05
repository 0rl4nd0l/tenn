# Deferred Phase 2 Prompt

You are Codex working on Tenn.

Task: Run Cockpit Web Contract Gaps Phase 2 for route parity only.

Lane: Reporting primary, Query Orchestration secondary.

Mode: AUDIT MODE first. SAFE EXTENSION MODE only after preflight confirms no overlap with dirty files.

Inputs:
- Start from `reports/cockpit_web_contract_gaps_phase1_20260505T180041+1000/02_gap_matrix.md`.
- Do not touch news/Qdrant, memory fanout, extraction, parser routing, financial truth, or marketplace product scoring.

Scope:
- Decide backend-owned route contracts for Watchlist web parity.
- Decide backend-owned route contract for Commentary recent sources.
- Confirm eBay sync runtime owner and add Next BFF coverage only if route parity requires it and marketplace dirty files are clean.

Hard limits:
- Do not implement broad Watchlist CRUD unless explicitly approved.
- Do not design a Commentary recent registry without explicit approval.
- Do not wire chat learning scorer.
- Do not rewrite source-label taxonomy.
- Do not add frontend-owned retrieval or any direct Qdrant/Postgres access from Cockpit UI.

Required output:
- Route contract proposal with exact method/path/request/response shapes.
- Collision report.
- Validation plan.
- Explicit defer list for anything requiring schema, store mutation, or product design.
