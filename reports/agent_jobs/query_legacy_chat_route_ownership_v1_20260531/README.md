# Legacy Chat Route Ownership Audit

Issue: https://github.com/0rl4nd0l/tenn/issues/150

## Decision

`KEEP_OPEN_NEEDS_IMPLEMENTATION_DECISION`.

The audit completed the ownership classification, but it did not integrate the parked legacy evidence-envelope work and did not retire the legacy route. The issue should remain open until Tenn explicitly chooses one path:

1. Keep `/chat` and `/api/chat`, then harden them with a documented/versioned compatibility envelope and focused route tests.
2. Retire or deprecate `/chat` and `/api/chat`, then validate known callers/docs and preserve `/api/cockpit/chat`.

## Current Route Ownership

- `POST /chat`: live legacy backend chat API from `financial-engine_v2/backend/app/routes/chat.py`.
- `POST /api/chat`: same legacy backend handler, mounted with `/api` prefix.
- `POST /api/cockpit/chat`: current Cockpit web chat route from `financial-engine_v2/backend/app/routes/cockpit_api.py`.
- Cockpit web UI: uses `/api/cockpit/chat`, not the legacy `/chat` or `/api/chat` route.

## Key Evidence

- `financial-engine_v2/backend/app/main.py:96-98` mounts `chat_router` both without a prefix and with `prefix="/api"`.
- `financial-engine_v2/backend/app/routes/chat.py:156-169` defines the legacy `@router.post("/chat")` handler.
- `financial-engine_v2/backend/app/routes/chat.py:138-141` wraps analysis responses as `{"type": "analysis", "content": ...}` rather than a route-level versioned compatibility envelope.
- `financial-engine_v2/backend/app/services/tenn_chat.py:733-753` emits per-source `evidence_label`, `evidence_labels`, and `claim_verified`.
- `financial-engine_v2/backend/app/services/tenn_chat.py:794-813` emits response-level `evidence_labels`, `source_coverage_status`, and `evidence_status`.
- Current-turn search found `SOURCE_LABEL_TAXONOMY_VERSION` and `source_label_taxonomy_version` in `shared/evidence_labels.py`, `query_orchestrator.py`, `cockpit_api.py`, and `test_evidence_label_semantics.py`, but not in `routes/chat.py` or `tenn_chat.py`.
- `cockpit-ui/lib/api-client.ts:671-792` sends both blocking and SSE web chat requests to `/api/cockpit/chat`.
- `financial-engine_v2/backend/app/routes/cockpit_api.py:9927-10034` owns the Cockpit route and returns the `done` event payload with sources and routing metadata for non-streaming mode.
- `docs/architecture/19_backend_api_surface.md:93-98` documents `/chat` and `/api/chat` as the legacy chat endpoint, and `docs/architecture/19_backend_api_surface.md:109-120` documents `/api/cockpit/chat` separately.
- `docs/architecture/19_backend_api_surface.md:296-298` says the chat endpoint is intentionally exposed at both `/chat` and `/api/chat`.
- `docs/architecture/21_cockpit_client_contract.md:63` defines `/api/cockpit/chat` as the Cockpit chat route relative to `/api/cockpit`.
- `reports/agent_jobs/query_legacy_chat_merge_readiness_audit_v1/README.md` records parked compatibility commit `9fc3d158f0cab218ae17343c00a56cf4d66cc240`, but the current branch does not contain that commit.

## Findings

1. The route split is real and current: legacy backend chat and Cockpit web chat are separate route contracts.
2. The legacy route is not source-label empty. It receives source labels from `chat_with_tenn()`.
3. The legacy route still lacks the route-level `SOURCE_LABEL_TAXONOMY_VERSION`/`source_label_taxonomy_version` contract that current Cockpit/query-orchestrator surfaces expose.
4. The legacy route wraps `chat_with_tenn()` output in a generic `type/content` shape, not the parked versioned compatibility envelope.
5. The Cockpit web UI currently targets `/api/cockpit/chat`, so route-parity audits must not treat legacy `/api/chat` validation as Cockpit web-chat validation.
6. Existing parked work appears relevant but is not integrated into the current branch. This audit did not validate a cherry-pick or run the parked branch tests.

## DATA_MISSING

- No live HTTP smoke was run for `/chat`, `/api/chat`, or `/api/cockpit/chat`.
- No external caller/access-log evidence was inspected for legacy route usage.
- No implementation/deprecation decision was made.
- No compatibility envelope was integrated or tested on this branch.
- No follow-up implementation issue was created; #150 remains the current tracker.

## No-Mutation Attestation

- No backend, frontend, runtime, retrieval, memory, DB, Qdrant, news, extraction, prompt, parser, gold-label, model, or service-config file was changed.
- No live chat request was sent.
- No production data was accessed.
- No GitHub issue was closed.

## Next Safe Step

Use a separate implementation task card if Tenn chooses to keep the legacy route. That task should integrate or supersede the parked envelope work on a clean isolated branch, add focused `/chat` and `/api/chat` route tests, and prove `/api/cockpit/chat` remains on its existing contract.
