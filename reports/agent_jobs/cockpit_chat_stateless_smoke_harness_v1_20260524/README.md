# Cockpit Chat Stateless Smoke Harness

Job: `cockpit_chat_stateless_smoke_harness_v1_20260524`
Date: 2026-05-24
Status: canonical integration validated

Lane: Query Orchestration
Worktree: `/home/l4nd0/tenn-cockpit-chat-stateless-smoke-harness-integrate-v1-20260524`
Branch: `integrate/cockpit-chat-stateless-smoke-harness-v1-20260524`
Base HEAD: `cde9c26d37e51373bf13dee2c9ce1245883b33b4`
Source implementation commit: `f3f76b0e8c8ab8a1fd795a61d650753e8337c074`
Execution mode: SAFE EXTENSION
Collision risk: MEDIUM, contained by isolated worktree and shared registry claim

## Confirmed Facts

- Shared canonical worktree `/home/l4nd0/tenn` had unrelated untracked task-card dirt, so this task used a clean isolated worktree from current HEAD.
- Canonical `/home/l4nd0/tenn` resolved to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` on branch `migration/clean-runtime-baseline-reconstruct-v1` at `cde9c26d37e51373bf13dee2c9ce1245883b33b4` before integration.
- The first direct canonical claim attempt was blocked only by pre-existing untracked task cards outside this job's allowed files; integration continued from a clean sibling worktree at the same HEAD.
- Shared registry had no active jobs before claim.
- Task card validation passed.
- Registry claim succeeded for `cockpit_chat_stateless_smoke_harness_v1_20260524`.
- Existing `/api/cockpit/chat` normal behavior is unchanged by default: requests without `stateless_smoke` still pass `persist_chat=True`, run delivery finalization, and allow auto-flag handoff.
- Stateless smoke mode requires both JSON `stateless_smoke: true` and header `X-Tenn-Stateless-Smoke: 1`.
- Stateless smoke mode passes `persist_chat=False` into `CockpitService.chat_stream`.
- Stateless smoke mode uses an internal one-off `stateless-smoke-*` session id, so a smoke request does not read or write a caller's existing chat session.
- Stateless smoke mode skips `_finalize_delivered_chat_response()` and `_maybe_auto_flag_chat_response()`.
- `CockpitService.chat_stream(..., persist_chat=False)` skips user/assistant `StateStore` chat-message persistence, recent YouTube option memory, and turn diagnostics.
- The existing source envelope and chat evidence guard still run, including the CSL filing-only price-trend guard.

## Architecture Review

| Rule source | Status | Explanation |
| --- | --- | --- |
| `docs/architecture/SYSTEM_CONTRACT.md` backend authority | COMPLIANT | Backend owns the chat response envelope; Cockpit remains a client. |
| `docs/architecture/SYSTEM_CONTRACT.md` retrieval boundary | COMPLIANT | No retrieval ranking, Qdrant access, Postgres access, or source selection logic changed. |
| `docs/architecture/SYSTEM_CONTRACT.md` pipeline/data invariants | COMPLIANT | No extraction, financial truth, vector IDs, embeddings, normalization, or canonical data writes changed. |
| `.cursor/rules/*` architecture-check rule files | DATA_MISSING | `.cursor/rules/` is absent in this checkout; `SYSTEM_CONTRACT.md` was used as the authoritative fallback. |

Verdict: APPROVED.

## Implementation

- Added `stateless_smoke` to `CockpitChatRequest`.
- Added explicit header gate: `X-Tenn-Stateless-Smoke: 1`.
- Routed stateless smoke requests through the same `/api/cockpit/chat` non-streaming and streaming response-envelope code.
- Added `persist_chat` to `CockpitService.chat_stream`, defaulting to `True`.
- Refactored direct-continuity metadata setup so non-persist mode can return a complete response without writing state.
- Marked stateless smoke responses with `routing_metadata.chat_persistence=disabled` and `routing_metadata.stateless_smoke=true`.
- Preserved normal response shape for non-smoke calls; stateless smoke top-level fields are emitted only for stateless smoke requests.

## CSL Smoke Fixture

- Non-stream CSL fixture: context-only Appendix 3C buy-back source plus bearish/current price-trend text.
- Stream CSL fixture: same evidence class and trend text.
- Expected metadata observed in tests:
  - `source_coverage_status=missing_required_evidence`
  - `market_data_missing`
  - `unsupported_or_not_verified`
  - `unsupported_claim_families=["market_price_or_technical_trend"]`
  - `chat_persistence=disabled`

## No-Mutation Boundary

- No live chat prompt was sent.
- No runtime, Docker, cron, systemd, model/GPU, Qdrant, Postgres, news SQLite, Tenn memory, financial truth, extraction, or parser-routing mutation was performed.
- This task changed only backend route/service code, focused backend tests, the task card, and report artifacts.

## Code Review

Code-review pass found no critical or warning findings after the session-id isolation adjustment. The main review concern was that stateless smoke should not accidentally read an existing thread; the implementation now uses a generated `stateless-smoke-*` session id for smoke calls.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_chat_stateless_smoke_harness_v1_20260524.md`: PASS.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_chat_stateless_smoke_harness_v1_20260524.md`: PASS.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_chat_stateless_smoke_harness_v1_20260524.md`: PASS.
- `PYTHONPYCACHEPREFIX=/tmp/tenn_stateless_smoke_integrate_pycache python3 -m compileall -q financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/app/services/cockpit_service.py financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py`: PASS.
- `/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python -m pytest -q financial-engine_v2/backend/tests/test_chat_evidence_guard.py financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py`: PASS, `66 passed`.
- `/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python -m ruff check financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/app/services/cockpit_service.py financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py`: PASS.
- Final artifact JSON, `git diff --check`, task-card `check-diff`, registry release, and final status are recorded in `validation.json`.

## Files Changed

- `docs/agent_tasks/cockpit_chat_stateless_smoke_harness_v1_20260524.md`
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/backend/app/services/cockpit_service.py`
- `financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py`
- `reports/agent_jobs/cockpit_chat_stateless_smoke_harness_v1_20260524/README.md`
- `reports/agent_jobs/cockpit_chat_stateless_smoke_harness_v1_20260524/status.json`
- `reports/agent_jobs/cockpit_chat_stateless_smoke_harness_v1_20260524/validation.json`
- `reports/agent_jobs/cockpit_chat_stateless_smoke_harness_v1_20260524/diff-check.json`

## Files Intentionally Not Touched

- Qdrant, Postgres, news SQLite, Tenn memory stores, financial truth, extraction, parser routing, Docker, cron, systemd, runtime topology, model/GPU configuration, frontend UI, old worktrees.

## Runtime Activation Boundary

- The harness is validated on the canonical-base integration branch.
- It becomes available to the running backend only after canonical is fast-forwarded/merged and the backend process is serving that updated source.
- No restart or runtime topology mutation was performed in this integration task.

## CSL Stateless Smoke Command

Once the running backend is serving this code, run the CSL live smoke against `/api/cockpit/chat` with:

```bash
curl -sS -X POST http://127.0.0.1:8000/api/cockpit/chat \
  -H 'Content-Type: application/json' \
  -H 'X-Tenn-Stateless-Smoke: 1' \
  -d '{"message":"what does the evidence say about CSL price trend, buybacks, tariffs, and financials?","ticker":"CSL","stream":false,"stateless_smoke":true}'
```

## Project Memory Save Recommendation

Save that `integrate/cockpit-chat-stateless-smoke-harness-v1-20260524` carries `f3f76b0e8c8ab8a1fd795a61d650753e8337c074` onto canonical-base `cde9c26d37e51373bf13dee2c9ce1245883b33b4`, adding explicit header-gated `stateless_smoke` support to `/api/cockpit/chat`, using `persist_chat=False`, one-off smoke session ids, and CSL filing-only price-trend regressions to avoid chat-history contamination before live prompt tests.
