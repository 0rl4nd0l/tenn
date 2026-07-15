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

## Controlled activation proof

- Launcher regression suite: `14 passed`.
- Focused routing/provenance suite: `53 passed`.
- Target containers recreated: backend, worker, and GPU worker only, using
  `docker compose ... up -d --no-deps --force-recreate`.
- Forbidden service identities remained unchanged: Postgres, Qdrant, Redis
  state, and host llama router; UI remained absent and was not restarted.
- Normal stateless chat: HTTP 200, `type=done`, `source=api`, model
  `claude-sonnet-4-6`, persistence disabled.
- GPU-exclusive token proof: chat routing reason `gpu_exclusive_active`.
- Non-metric JSON tool proof: provider `anthropic`, model
  `claude-sonnet-4-6`, routing reason `metric_extraction_active`.
- Cockpit state DB: zero count/timestamp delta across `chat_messages`,
  `chat_sessions`, and `session_summaries`.
- News memo store: unchanged; mtime predates both proof requests.
- Host llama journal: no attributable chat completion during either proof.
- Final health/readiness: HTTP 200; extraction inactive; proof token count zero;
  Celery active, reserved, and scheduled work empty.

## Scope limitation

The extraction-active route was exercised through the real shared
GPU-exclusive routing-state token with a 180-second TTL. No real extraction was
started. This proves the route class without claiming a production extraction
run. The UI outage on port 8081 predates activation and was not repaired.
