# Remaining Risks

## Not Fixed In This Lane

- Source drawer rendering was not redesigned. Source metadata is now available for a future targeted UI pass.
- Full claim-by-claim proof mapping is not implemented. `claim_verified` remains a conservative source-level label based on direct source/support matching, not a complete proof graph.
- Existing architecture invariant tests still report pre-existing SQLite runtime imports. This task did not add or remove those imports.
- An unrelated holdings-screen Vitest failure was observed when running a broad UI command. Focused chat-source tests passed.
- Unknown/unclassified sources are safely non-verified, but upstream source producers should still be cleaned up to provide explicit source types over time.

## Safety Boundaries Confirmed

- Ingestion touched: no
- Qdrant mutated: no
- news.sqlite mutated: no
- Memory mutated: no
- Retrieval rankings changed: no
- Synthesis prompts broadly changed: no
- Financial truth extraction changed: no
- Raw thinking exposed: no

## Blockers

No blocker remains for Source Label Semantics v1. Remaining work belongs in a Reporting/UI follow-up for the source drawer and a separate architecture cleanup lane for pre-existing SQLite invariant failures.
