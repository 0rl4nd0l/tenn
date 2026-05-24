# CSL Stateless Smoke Summary

## Result

- Runtime/no-mutation: PASS
- Evidence metadata guard: PASS
- Visible answer guard: FAIL
- Overall CSL criteria: FAIL

## Request

- Endpoint: `POST /api/cockpit/chat`
- Header: `X-Tenn-Stateless-Smoke: 1`
- Query: `what does the evidence say about CSL price trend, buybacks, tariffs, and financials?`
- HTTP status: `200`
- Session: `stateless-smoke-b7b9998623824dee9285cbebdbefaa13`

## Observed Metadata

- `chat_persistence`: `disabled`
- `stateless_smoke`: `True`
- `visible_source_count`: `10`
- `claim_verified_source_count`: `0`
- `evidence_labels`: `['context_only', 'financial_truth', 'local_news_context', 'market_data_missing', 'missing_required_evidence', 'operational_trace', 'unknown_unclassified', 'unsupported_or_not_verified']`
- `unsupported_claim_families`: `['market_price_or_technical_trend']`
- `missing_evidence_categories`: `['market_data']`

## Assessment

The live backend now exposes the stateless harness and did not persist chat history or append memory read events. Metadata correctly marks market evidence as missing and the market-price/technical family as unsupported.

The user-visible answer still fails the full CSL criteria because it includes an unqualified company-memory price movement line and does not visibly surface `market_data_missing`, `unsupported_or_not_verified`, or `metric_extraction_missing`/`DATA_MISSING` in the answer text.

Unsafe remaining examples:

- `CSL's share price dropped amid chaotic trading after CEO resignation announcement`
- `no canonical financial rows were returned` appears, but without a visible `metric_extraction_missing` or `DATA_MISSING` label.
