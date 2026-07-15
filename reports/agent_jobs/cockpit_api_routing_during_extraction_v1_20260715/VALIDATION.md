# Validation

## Passed

- TDD RED: keyword chat called local llama.cpp before HybridRouter construction.
- TDD GREEN: keyword chat routes through the configured API client and does not
  call local llama.cpp.
- TDD RED/GREEN: extraction-active news and other non-metric JSON calls route
  to Anthropic before local routing; metric extraction remains local; missing
  API configuration fails fast.
- TDD RED/GREEN: news memo provenance records the effective Anthropic route.
- TDD RED/GREEN: Anthropic adapter default migrated from the rejected retired
  model to `claude-sonnet-4-6`.
- Cockpit/Claude/config regression suite: `160 passed`, `48 subtests passed`.
- Backend/news routing regression suite: `30 passed`.
- Earlier focused Cockpit routing suite: `133 passed`, `48 subtests passed`.
- Final stateless Anthropic smoke: `ANTHROPIC_STATELESS_SMOKE=PASS`,
  `MODEL=claude-sonnet-4-6`.
- `ruff check`: passed on all modified Python source and test files.
- `py_compile`: passed on all modified Python source and test files.
- `git diff --check`: passed.
- Task card validation and exact allowlist check: passed.
- Code review: `SUCCESS`, no critical findings, warnings, or suggestions.

The pytest runs emitted one pre-existing warning for unknown config option
`asyncio_default_fixture_loop_scope`. The backend uv run also reported the
existing ignored requirements-file extra-index warning.

## Not proven

The live Cockpit process was deliberately not restarted. No live chat turn was
run against this branch while a real metric extraction owned the shared router.
See `RUNTIME_FUNCTIONALITY_PROOF.md`.
