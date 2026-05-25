# Recent News Positive Claim-Verified Fixture

Status: `complete_safe_extension`.

This child added an upstream positive fixture proving that deterministic recent-news/event evidence can still satisfy recent-news/update claims after the stricter source-label sufficiency guard.

## Confirmed

- The source-label/recent-news guard is in `financial-engine_v2/backend/app/services/chat_evidence_guard.py`.
- Recent-news/update claims require the deterministic `recent_news_event` evidence category.
- `context_only`, filing-only, price-only, and numeric `financial_truth` context remain insufficient for recent-news/update claims.
- Raw `claim_verified` or `supports_claim` booleans cannot self-promote an insufficient source.
- UI metadata now reports `claim_verified_source_count` after evidence guard enrichment so recent-news/update claims count only sufficient claim-verified sources.

## Implementation

- Added a direct guard regression test for `source_role_labels: ["recent_news_event"]`.
- Added UI metadata tests covering the happy path, `context_only` recent-news context, and `financial_truth` numeric context.
- Added a narrow helper in `cockpit_api.py` to count claim-verified sources against the active evidence requirements.

## Validation

- `/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_chat_evidence_guard.py financial-engine_v2/backend/tests/test_build_ui_sources.py -q`
- `/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python -m ruff check financial-engine_v2/backend/app/services/chat_evidence_guard.py financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_chat_evidence_guard.py financial-engine_v2/backend/tests/test_build_ui_sources.py`

## No-Write Boundary

No Qdrant, news SQLite, memory, Postgres, parser, extraction, prompt, routing ranker, or production data writes were performed.
