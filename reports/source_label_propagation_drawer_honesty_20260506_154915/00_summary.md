# Summary

Lane: Provenance
Supporting lane: Reporting
Execution mode: SAFE EXTENSION MODE
Collision risk: MEDIUM

## Verdict

- G001 historical chat session reload: fixed for newly saved/current-turn messages by persisting normalized source-label metadata with assistant chat rows and returning it from `/api/cockpit/chat/sessions/{session_id}`. Legacy rows without metadata reload as `unknown_unclassified`/non-verified fallback.
- G002 attached-source evidence: fixed for attached-source evidence already included in prompt/context by emitting it as labelled `context_only` source metadata. Synthetic score `1.0` does not make it `claim_verified` or `financial_truth`.
- G004 generic UI wording: fixed in `terminal-message.tsx`; the generic `Financial facts: source-backed when shown below` wording was removed and replaced by role-specific evidence summary text.

## Safety

- Ingestion touched: no
- Qdrant mutated: no
- `news.sqlite` mutated: no
- Memory mutated: no
- Financial truth touched: no
- Retrieval ranking changed: no
- Source-label taxonomy redesigned: no
- Raw chain-of-thought exposed: no
