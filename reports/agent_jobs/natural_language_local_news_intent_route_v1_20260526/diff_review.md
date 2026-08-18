# Diff Review

## Scope

- `financial-engine_v2/cockpit/core/chat.py`
- `financial-engine_v2/cockpit/tests/test_chat_ticker_detection.py`
- `financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py`
- task card and report artifacts for this job

## Findings

No blocking findings.

## Review Notes

- The code change is limited to Cockpit chat intent routing.
- Natural-language ticker-news prompts now enter the existing
  `_try_news_shortcircuit()` path and still emit `news_search` evidence.
- Backend source-pack assembly remains unchanged.
- `chat_evidence_guard.py` remains untouched.
- No ticker-specific aliases or A2M/BHP/CSL/COH hardcoding were added to
  production code.
- Filing/document, financial-analysis, price, chart, and market-wide news
  wording is excluded from the new natural-news short-circuit.

## Architecture Review

- Target layer: Query Orchestration.
- Supporting layers: Provenance, Evaluation, Reporting, Repo Hygiene.
- Contract basis: `docs/architecture/SYSTEM_CONTRACT.md` requires backend
  authority for retrieval/source-pack truth and prohibits alternate retrieval,
  fallback masking, or cross-layer store access.
- `.cursor/rules/` was not present in this checkout, so that rule-file review is
  `DATA_MISSING`; the mandatory system contract was read and applied.
- No embeddings, vector IDs, vector dimensions, embedding models, DB schema, or
  storage writes were changed.
- No DB, Qdrant, news-store, projection, parser, financial truth, memory,
  runtime/model/GPU config, or UI redesign mutation occurred.

## Verdict

Approved for focused validation and integration. The change reuses the landed
claim-verified local-news source-pack path rather than altering evidence
verification or guard semantics.
