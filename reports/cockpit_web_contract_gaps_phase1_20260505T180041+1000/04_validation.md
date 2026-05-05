# Validation

Validation status: focused validation passed for changed surfaces. The named Vitest command from the prompt is recorded separately because, as written in this repo, it selected unrelated test files outside this change.

Commands and results:
- `PYTHONDONTWRITEBYTECODE=1 financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/cockpit/tests/test_chat_attached_sources.py -q -p no:cacheprovider` - passed: `4 passed, 6 warnings`.
- `financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py -q` - passed: `46 passed`.
- `financial-engine_v2/.venv/bin/python -m ruff check financial-engine_v2/cockpit/tests/test_chat_attached_sources.py` - passed: `All checks passed!`.
- `pnpm --dir cockpit-ui exec tsc --noEmit` - passed.
- `pnpm --dir cockpit-ui exec eslint components/cockpit/chat/chat-screen.tsx components/cockpit/chat/terminal-message.tsx lib/cockpit-types.ts app/api/cockpit/commentary/ephemeral-index/route.ts 'app/api/cockpit/commentary/ephemeral-index/[sessionId]/route.ts'` - passed.
- `git diff --check` - passed.

Frontend test command note:
- `pnpm --dir cockpit-ui test -- chat-screen terminal-message sources-drawer watchlist` did not behave as a narrow focused command in this repo. It ran 28 test files and failed unrelated tests in `components/cockpit/holdings/holdings-screen.test.tsx` and `components/cockpit/marketplace/mission-screen.test.tsx` on the first attempt, then failed the same unrelated Holdings assertion on the second attempt. Those files were not changed by this phase.
- DATA_MISSING: no `chat-screen` test file exists in `cockpit-ui/components/cockpit/chat/`.
- Nearest focused command run: `pnpm --dir cockpit-ui exec vitest run components/cockpit/chat/terminal-message.test.tsx components/cockpit/chat/sources-drawer.test.tsx components/cockpit/watchlist/watchlist-screen.test.tsx lib/api-client.test.ts` - passed: `4 passed (4)`, `15 passed (15)`.

Pre-fix evidence:
- `test_chat_attached_sources.py` failed one test with `AttributeError: 'ChatController' object has no attribute '_recent_youtube_video_options'`.

No backend service/session implementation files were touched, so `test_cockpit_service_session_threads.py` is not required by the task condition.

Live-store checks:
- No Qdrant mutation commands were run.
- No SQLite mutation commands were run by this phase.
- No news ingestion, backfill, or service restart commands were run.
