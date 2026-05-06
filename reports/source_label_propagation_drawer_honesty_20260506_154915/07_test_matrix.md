# Test Matrix

| Requirement | Test Evidence |
|---|---|
| Historical reload preserves evidence roles | `test_chat_message_metadata_round_trips_for_session_reload`, `test_chat_session_reload_preserves_saved_source_labels` |
| Current-turn answer saved with labels | `test_chat_session_reload_preserves_saved_source_labels` posts `/api/cockpit/chat`, then reloads session |
| Legacy missing metadata does not become claim verified | `test_legacy_chat_session_reload_uses_unclassified_safe_fallback` |
| Attached source included in prompt/context | Existing `test_keyword_chat_inlines_attached_source_context`; strengthened to assert context labels |
| Attached source emitted as labelled source metadata | `test_attached_source_is_emitted_as_context_only_not_claim_verified` |
| Attached source not financial truth/claim verified from score | `test_attached_source_is_emitted_as_context_only_not_claim_verified` |
| Generic UI wording removed | `terminal-message.test.tsx` context-only and no-hit assertions |
| Role-specific wording appears | `terminal-message.test.tsx` asserts `Verified sources`, `Context sources`, and `No relevant source found` |
| A2M local news remains local news context | Existing `test_news_retrieval_eval.py -k "A2M or local_news or degraded"` passed |
| Holdings remains local personal data | Existing `test_cockpit_api_chat_stream.py -k "attached or holdings or runtime"` passed |
| Memory context remains non-verified | Existing `test_build_ui_sources.py` memory test passed |
| Degraded runtime remains surfaced | Existing runtime tests passed in focused selectors |
