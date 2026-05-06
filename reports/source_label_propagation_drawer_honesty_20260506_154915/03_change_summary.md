# Change Summary

## Files Changed

- `financial-engine_v2/cockpit/storage/state.py`
- `financial-engine_v2/cockpit/core/chat.py`
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `cockpit-ui/lib/api-client.ts`
- `cockpit-ui/components/cockpit/chat/chat-screen.tsx`
- `cockpit-ui/components/cockpit/chat/terminal-message.tsx`
- `financial-engine_v2/backend/tests/test_build_ui_sources.py`
- `financial-engine_v2/backend/tests/test_cockpit_api_chat_sessions.py`
- `financial-engine_v2/cockpit/tests/test_chat_attached_sources.py`
- `financial-engine_v2/cockpit/tests/test_state_chat_sessions.py`
- `cockpit-ui/components/cockpit/chat/terminal-message.test.tsx`
- `reports/source_label_propagation_drawer_honesty_20260506_154915/*`

## Implementation Notes

- Added additive `metadata_json` storage for chat messages. Existing rows are not rewritten.
- API session reload now returns saved metadata and safe fallback metadata for legacy assistant rows.
- Attached-source evidence is visible as context-only evidence.
- The chat UI no longer collapses all source counts into source-backed financial-fact wording.
