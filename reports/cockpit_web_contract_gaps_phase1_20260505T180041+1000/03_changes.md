# Changes

Files changed by this phase:
- `cockpit-ui/components/cockpit/chat/chat-screen.tsx`
- `cockpit-ui/components/cockpit/chat/terminal-message.tsx`
- `cockpit-ui/lib/cockpit-types.ts`
- `cockpit-ui/app/api/cockpit/commentary/ephemeral-index/route.ts`
- `cockpit-ui/app/api/cockpit/commentary/ephemeral-index/[sessionId]/route.ts`
- `financial-engine_v2/cockpit/tests/test_chat_attached_sources.py`
- `reports/cockpit_web_contract_gaps_phase1_20260505T180041+1000/*`

F1 fixed:
- Removed chat message `thinking` storage from frontend feedback snapshots.
- Removed frontend SSE `thinking` event type from Cockpit chat types.
- Removed `thinking` event handling from chat streaming.
- Removed raw Assessment/Plan rendering from streamed and completed chat messages.
- Preserved safe status labels from backend `status` events.
- Did not add raw thinking SSE.

F4 fixed:
- Removed the hidden frontend call to `/api/cockpit/commentary/ephemeral-index`.
- Replaced unsupported BFF proxy behavior with explicit `501 unavailable` responses for ephemeral index POST/DELETE.
- Did not implement semantic ephemeral retrieval.
- Did not add frontend-owned retrieval.

F5 fixed:
- Added `_recent_youtube_video_options = []` to the focused test fixture that bypasses `ChatController.__init__`.
- Did not alter runtime attached-source logic.

Unchanged by design:
- Watchlist CRUD was not implemented because route ownership and storage semantics need a separate backend contract decision.
- Commentary recent was not implemented because a backend source registry/recent-source contract is a separate design task.
- Chat learning scorer was not wired because it would change learning semantics and persistence behavior.
- eBay sync product logic was not changed; runtime owner was inspected only.
