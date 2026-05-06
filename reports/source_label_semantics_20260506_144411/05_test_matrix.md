# Test Matrix

| Required Case | Coverage |
| --- | --- |
| A2M recall local news included | `financial-engine_v2/backend/tests/test_news_retrieval_eval.py` asserts A2M recall sources include `local_news_context`, `claim_verified`, and claim coverage when supporting evidence matches. |
| Ticker-specific A2M query includes local news source metadata | `test_news_retrieval_eval.py` covers ticker-filtered local news source metadata produced by `chat_with_tenn`. |
| Recall claim receives claim/source support only if retrieved source directly supports it | `test_news_retrieval_eval.py` includes a direct-support case and a non-matching context-only case. |
| A2M local news missing/no-hit | `test_news_retrieval_eval.py` asserts expected local news gap emits `missing_required_evidence` and `no_hit`, not complete coverage. |
| No-hit tool result | `financial-engine_v2/backend/tests/test_build_ui_sources.py` and `test_cockpit_api_chat_stream.py` assert no-hit sources are not claim verified. |
| Runtime degraded state | `test_cockpit_api_chat_stream.py`, `test_news_retrieval_eval.py`, and `financial-engine_v2/cockpit/tests/test_agent_loop_synthesis_timeout.py` assert degraded runtime metadata. |
| Holdings | `test_cockpit_api_chat_stream.py` and existing holdings tests assert local personal data remains separate from financial truth. |
| Memory context | `test_build_ui_sources.py` asserts memory source labels as memory/context, not financial truth or claim verified. |
| External web context | `test_build_ui_sources.py` asserts web source labels external context, not financial truth or claim verified by default. |
| Unknown source type | `test_build_ui_sources.py` asserts unknown/unclassified fallback is non-verified. |
| UI trust label | `cockpit-ui/components/cockpit/chat/terminal-message.test.tsx` asserts claim-supported and no-hit audit rendering, and absence of generic source-backed text for no-hit. |

## Tests Preserving Existing Boundaries

- `financial-engine_v2/cockpit/tests/test_chat_holdings_intent_routing.py`
- `financial-engine_v2/backend/tests/test_cockpit_api_preferences.py`

These focused validations passed and preserve current local holdings behavior.
