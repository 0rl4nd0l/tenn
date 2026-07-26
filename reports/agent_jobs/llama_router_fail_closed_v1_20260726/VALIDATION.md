# Validation

## Red

- Command: `uv run --no-project --with pytest python -m pytest -p
  no:cacheprovider -q
  scripts/test_llama_server_launchers.py::test_run_llama_server_fails_closed_when_router_capability_is_missing`
- Result: exit 1, expected failure; existing launcher returned 0 and started the
  fake single-model server.

## Green

- Same focused regression: 1 passed.
- Complete `scripts/test_llama_server_launchers.py`: 13 passed.
- `bash -n scripts/run_llama_server.sh`: passed.
- `git diff --check`: passed.
- Code review: passed with no findings.

The ephemeral validation environment used `/tmp/tenn-uv-cache-llama-router-fail-closed`;
no repository dependency or runtime environment was changed. Pytest emitted
one unrelated warning for an unknown repository asyncio configuration option.

## Runtime boundary

No llama process was started, no document was processed, and no store, model,
or host configuration was changed. Live runtime functionality remains
`DATA_MISSING` pending separate activation authorization.
