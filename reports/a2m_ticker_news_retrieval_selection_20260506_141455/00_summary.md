# Summary

The A2M trace showed that local ticker-filtered retrieval can select the recall articles, while broad no-ticker semantic retrieval did not. The fix therefore changes selection, not ingestion.

Files changed:

- `financial-engine_v2/backend/app/services/tenn_chat.py`
- `financial-engine_v2/cockpit/core/agent_loop.py`
- `financial-engine_v2/backend/tests/test_news_retrieval_eval.py`
- `financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py`
- `financial-engine_v2/cockpit/tests/test_agent_loop.py`
- `reports/a2m_ticker_news_retrieval_selection_20260506_141455/*`

Retrieval verdict:

- A ticker-specific A2M chat query now considers ticker-filtered news before broad no-ticker semantic retrieval is treated as complete.
- Synthetic A2M regression fixtures using audited recall article metadata prove the recall article is retained in prompt/context and source metadata when ticker-filtered news retrieval returns it.
- Broad semantic behavior remains unchanged when no ticker is resolved.
- Holdings/local personal data routing is unaffected by the new prefetch guard and remains covered by existing stream tests.

Still out of scope:

- Source-label semantics remain unfixed and belong to a separate Reporting/Provenance lane.
- Partial entity-linking drift remains unfixed. It is not a blocker for this v1 selection fix because the audit confirmed three core recall articles are A2M-linked, but it remains a blocker for full article coverage.
