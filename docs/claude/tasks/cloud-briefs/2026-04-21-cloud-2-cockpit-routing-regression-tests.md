# Cloud-2: Cockpit Routing Regression Tests

## Goal

Harden regression coverage for shared-router mutex, local/API fallback behavior, and follow-up or intent routing.

## Scope

- Read:
  - `financial-engine_v2/cockpit/core/actions.py`
  - `financial-engine_v2/cockpit/core/tool_executor.py`
  - `financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py`
  - `financial-engine_v2/cockpit/tests/test_tool_executor.py`
- Write:
  - Test files only, unless a tiny testability hook is required.

## Invariants (Do Not Break)

- No routing policy changes beyond what test coverage requires.
- No new fallback layer that bypasses backend API authority.
- No runtime config contract drift.

## Validation

```bash
python -m ruff check financial-engine_v2/cockpit/tests/test_tool_executor.py financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py
pytest -c pytest.ini financial-engine_v2/cockpit/tests/test_tool_executor.py -q
pytest -c pytest.ini financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py -q
```

## Deliverable

- New or updated regression tests covering:
  - local timeout to API fallback path
  - routing behavior for market-wide vs ticker-specific prompts
  - shared-router extraction mutex behavior
- Short risk note for any still-uncovered routing path.
