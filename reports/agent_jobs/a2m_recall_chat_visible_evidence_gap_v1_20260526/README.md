# A2M Recall Chat Visible Evidence Gap

Issue: #87, `[Query Orchestration] A2M recall chat answer lacks required visible evidence`

## Decision

Keep #87 open as `DATA_MISSING`. Current code/test evidence shows the guard can
represent claim-verified A2M recall news correctly, and can reject context-only
or non-news sources for recent-update claims. The missing evidence is the live
chat response envelope: exact prompt/session, final `sources`, routing metadata,
runtime URL, and active substrate proof are still unavailable in this pass.

## Current Evidence

- The issue body records the reported visible gaps:
  - `market_data_missing`
  - `unsupported_or_not_verified`
  - `metric_extraction_missing`
  - `insufficient_for_recent_news`
  - `missing_required_evidence`
- `chat_evidence_guard.py` requires a `recent_news_event` category for recent
  news/update claims, and that category requires claim-verified event-like
  news rather than no-hit, missing-required-evidence, or context-only sources.
- The guard also requires market/price evidence for price-trend claims and
  financial-statement/extracted-metric evidence for financial metric claims.
- The A2M recall fixture in `test_news_retrieval_eval.py` proves an A2M recall
  article can become `local_news_context` + `claim_verified` when it reaches
  synthesis as a ticker-filtered local-news source.
- Focused tests passed for:
  - A2M recall local-news source retained in prompt and visible sources.
  - Claim-verified news satisfying recent-update requirements.
  - Explicit recent-news-event roles satisfying recent-update requirements.
  - Mixed `context_only` labels blocking recent-news satisfaction.
  - Financial-truth numeric context not satisfying recent event claims.

## Runtime Probe

No current local frontend/backend was available for a safe live reproduction:
ports 3000, 3001, 8000, and 8001 had no listeners, and bounded curl probes to
the frontend chat endpoint and backend health route failed with connection
refused. No service was started for this audit.

## Adjacent Trackers

- #38 is closed and covered the earlier A2M news trace/retrieval blast-radius
  audit. It does not close the current chat response-envelope failure.
- #49 is open and adjacent for News page lookback request wiring, not this chat
  answer evidence envelope.
- #83 is open for news projection/materialization parity and remains relevant
  if active news substrate proof is missing.
- #104 / PR #176 cover cross-route evidence-envelope auditing and explicitly
  leave #87 as the A2M-specific visible-evidence owner.
- #122 is open for suggested-next action wiring, not the source envelope needed
  to verify the A2M answer.

## Safe Closeout Decision

Do not close #87 as fixed. Do not mutate source assembly, the evidence guard,
retrieval, or chat rendering from this evidence alone. The next safe step is a
dedicated live or captured-response replay that preserves the final
`sources` array, routing metadata, and active news/market/metric substrate
state without mutating DB, Qdrant, news, memory, or runtime config.

## Remaining DATA_MISSING

- Exact prompt that produced the pasted answer.
- Session id, runtime URL, branch, and commit at answer time.
- Final `/api/cockpit/chat` `sources` array for the answer.
- Final routing metadata for the answer.
- Proof that the A2M recall article exists or is missing in the active news
  substrate used by that response.
- Proof that market price and metric evidence were or were not attached before
  the answer made price-plunge or revenue-impact claims.
