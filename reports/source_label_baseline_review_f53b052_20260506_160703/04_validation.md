# Validation

## Commands Run

```bash
financial-engine_v2/.venv/bin/python -m pytest \
  financial-engine_v2/backend/tests/test_build_ui_sources.py \
  financial-engine_v2/backend/tests/test_cockpit_api_models.py \
  financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py \
  financial-engine_v2/backend/tests/test_cockpit_api_chat_sessions.py \
  financial-engine_v2/cockpit/tests/test_chat_attached_sources.py \
  financial-engine_v2/cockpit/tests/test_state_chat_sessions.py \
  -q
```

Result: passed, `124 passed, 6 warnings in 16.50s`. Warnings were existing Pydantic protected-namespace/deprecation warnings.

```bash
pnpm --dir cockpit-ui exec tsc --noEmit
```

Result: passed.

```bash
pnpm --dir cockpit-ui exec vitest run components/cockpit/chat/terminal-message.test.tsx
```

Result: passed, `1 passed`, `11 passed`.

```bash
pnpm --dir cockpit-ui exec eslint components/cockpit/chat/chat-screen.tsx components/cockpit/chat/terminal-message.tsx components/cockpit/chat/terminal-message.test.tsx lib/api-client.ts
```

Result: passed.

```bash
pnpm --dir cockpit-ui exec vitest run components/cockpit/chat/sources-drawer.test.tsx
```

Result: passed, `1 passed`, `2 passed`.

```bash
financial-engine_v2/.venv/bin/python -m ruff check \
  financial-engine_v2/backend/app/routes/cockpit_api.py \
  financial-engine_v2/cockpit/core/chat.py \
  financial-engine_v2/cockpit/storage/state.py \
  financial-engine_v2/backend/tests/test_build_ui_sources.py \
  financial-engine_v2/backend/tests/test_cockpit_api_chat_sessions.py \
  financial-engine_v2/cockpit/tests/test_chat_attached_sources.py \
  financial-engine_v2/cockpit/tests/test_state_chat_sessions.py
```

Result: passed, `All checks passed!`.

```bash
git diff --check
```

Result: passed.

## Not Run

Broad Playwright and broad backend/frontend suites were not run because the task requested focused validation and no browser smoke was needed for this audit.
