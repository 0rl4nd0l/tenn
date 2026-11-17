# Follow-up Recommendation

## Recommended next task

Create a separate Query Orchestration safe-extension task to make one explicit product decision:

1. Preserve and harden legacy `/chat` and `/api/chat`.
2. Deprecate legacy `/chat` and `/api/chat` after caller validation.

This audit should not make route-code changes because the relevant product files are contested Query Orchestration/runtime surfaces.

## Option A: Preserve and harden legacy routes

If legacy routes remain supported, implement a compatibility evidence envelope around the legacy analysis response while preserving existing clients:

- Keep the existing `{"type": "analysis", "content": ...}` shape unless a compatibility review approves a breaking change.
- Add route-level metadata or a documented compatibility envelope with `source_label_taxonomy_version`.
- Preserve `chat_with_tenn()` source labels and missing-source guard behavior.
- Add focused tests for degraded runtime, no-hit, context-only, claim-verified local news, memory/personal/web/news/financial-truth labels where applicable, and both `/chat` and `/api/chat` HTTP mounts.
- Use parked branch/report evidence from `safe/query-legacy-chat-envelope-compat-v1` and `reports/agent_jobs/query_legacy_chat_merge_readiness_audit_v1/README.md` as input, not as proof of current behavior.

## Option B: Deprecate legacy routes

If legacy routes should be retired:

- Validate current callers for `cockpit-ui/app/chat/route.ts` and any external docs/scripts using `/chat` or `/api/chat`.
- Add explicit docs stating `/api/cockpit/chat` is the Cockpit web chat contract.
- Provide a compatibility/deprecation period or endpoint warning if external callers still depend on the legacy shape.
- Do not silently remove or change `/chat` or `/api/chat`.

## Current audit closeout recommendation

- Use PR link text `Refs #150`.
- Do not use `Fixes #150` unless maintainers accept report-only route ownership classification as the full issue closeout.
- Keep a follow-up implementation tracker open until preserve-vs-deprecate is decided and validated.
