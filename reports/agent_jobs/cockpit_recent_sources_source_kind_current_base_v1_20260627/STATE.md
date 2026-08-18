# State

## Current State

- `VERIFIED`: Worktree is `/home/l4nd0/tenn-issue213-recent-source-kind-current-base-v1-20260627`.
- `VERIFIED`: Branch is `safe/issue213-recent-source-kind-current-base-v1-20260627`.
- `VERIFIED`: Base is `origin/migration/clean-runtime-baseline-reconstruct-v1@b92133455871f2a9be1f9030b2ef4abc995dfb9d`.
- `VERIFIED`: Guard preflight passed as `VALID_TASK_WORKTREE`.
- `VERIFIED`: Registry claim is active for `cockpit_recent_sources_source_kind_current_base_v1_20260627`.
- `VERIFIED`: Live task ledger append succeeded for `claimed` and `implementation_started`.

## Decision

Implement the deterministic mapping requested by #213:

- `market_commentary` -> `concat`
- `youtube_transcript` -> `ephemeral`
- `podcast_transcript` -> `ephemeral`

The UI uses a backend-provided `source_kind` when present and falls back to the same deterministic mapping for older or partial payloads.

## Docs Impact

- `docs_impact`: `DOCS_NOT_REQUIRED`
- `docs_checked`: `AGENTS.md`, `docs/README.md`, issue #213
- `docs_changed`: none
- `docs_followup`: none
- `reason`: The change is a narrow API/UI metadata contract fix; no durable docs routing or operator procedure changed.

## Model And Worker Routing

- `task_tier`: medium
- `recommended_model`: standard coding model
- `actual_model`: Codex GPT-5
- `why_this_model`: Focused backend response-contract and Cockpit UI callback change with tests.
- `worker_model_allowed`: false
- `worker_decision_limit`: No workers used; scope is narrow and same-surface coordination is simpler in one worktree.
- `escalation_needed`: false

## Boundaries Kept

- No DB, Qdrant, Redis, news store, memory store, source PDF, extraction output, gold-label, runtime/model/GPU/service config, or production data mutation.
- No source/evidence label relaxation.
- No chat router redesign.
- No source drawer visual redesign.

## Runtime Functionality Proof

No daemon, scheduler, ingestion, extraction, service start, or production runtime mutation was performed. Because this changes an API/UI route contract, the proof status is explicitly `PARTIAL` until live or CI-backed UI validation runs.

| Field | Evidence |
| --- | --- |
| intended output | `/api/commentary/recent` items expose `source_kind`; Cockpit Recent sources reattach preserves that source kind in attached-source request metadata. |
| live output location | Local FastAPI `TestClient` endpoint response for `/api/commentary/recent`; Cockpit UI source path `SourcesDrawer` -> `ChatScreen`; no live backend or browser runtime was started. |
| pre-run max timestamp or count | `DATA_MISSING`; no live service/data baseline captured because this slice did not start services or query production stores. |
| post-run max timestamp or count | `DATA_MISSING`; no live service/data post-run probe captured because this slice did not start services or query production stores. |
| rows/files inserted or updated after run start | Live data rows: 0. Git worktree files changed inside task-card scope only. |
| readiness/gate status | Backend focused test passed; local Cockpit UI validation blocked by missing local `vitest`/`eslint`; GitHub CI required before merge. |
| exact command/query used | `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_commentary_recent_endpoint.py -q`; `npm test -- components/cockpit/chat/sources-drawer.test.tsx`; `npm run lint -- components/cockpit/chat/sources-drawer.tsx components/cockpit/chat/chat-screen.tsx`. |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | PARTIAL |
| remaining blocker | Local Cockpit UI validation tools are unavailable; PR/GitHub CI must validate frontend before merge. |

result: PARTIAL
