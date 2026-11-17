# Legacy Chat Route Ownership Audit

Issue: https://github.com/0rl4nd0l/tenn/issues/150

## Decision

The route ownership decision is now evidence-backed and recorded:

- `POST /chat` and `POST /api/chat` are compatibility/legacy backend routes owned by `financial-engine_v2/backend/app/routes/chat.py`.
- `POST /api/cockpit/chat` is the Cockpit web chat route owned by `financial-engine_v2/backend/app/routes/cockpit_api.py` and consumed by current Cockpit UI chat clients.
- The current legacy routes include source/evidence labels inside `content` via `chat_with_tenn()`, but they do not expose a route-level versioned evidence envelope or `source_label_taxonomy_version`.
- The current Cockpit route exposes richer source/evidence metadata, visible-source enforcement, routing metadata, streaming events, and persisted metadata that includes `source_label_taxonomy_version`.
- The safest next product step is a separate safe-extension task to either harden the legacy routes with a compatibility evidence envelope and tests, or explicitly deprecate the legacy proxy/callers. This audit did not mutate route behavior.

## Current Evidence

### Mount ownership

- `financial-engine_v2/backend/app/main.py:95-98` creates the FastAPI app and mounts `chat_router` both without a prefix and with `prefix="/api"`.
- `financial-engine_v2/backend/app/routes/chat.py:156-169` implements `@router.post("/chat")`; because of the two mounts, the same handler serves both `POST /chat` and `POST /api/chat`.
- `financial-engine_v2/backend/app/main.py:113-114` mounts `cockpit_api_router` under `/api/cockpit`.
- `financial-engine_v2/backend/app/routes/cockpit_api.py:9927-10034` implements the Cockpit `@router.post("/chat")`, making the live route `POST /api/cockpit/chat`.

### Legacy route response contract

- `financial-engine_v2/backend/app/routes/chat.py:57-141` calls `chat_with_tenn()`, removes private `_pending_turn`, records session-memory quality metrics where available, and returns `{"type": "analysis", "content": _json_safe_value(content)}`.
- `financial-engine_v2/backend/app/routes/chat.py:142-153` degrades to the same `type="analysis"` wrapper with a degraded payload if analysis fails.
- `financial-engine_v2/backend/app/services/tenn_chat.py:387-404` assigns source labels such as `local_news_context`, `financial_truth`, `context_only`, and `claim_verified` for context rows.
- `financial-engine_v2/backend/app/services/tenn_chat.py:733-753` emits per-source `evidence_label`, `evidence_labels`, and `claim_verified`.
- `financial-engine_v2/backend/app/services/tenn_chat.py:777-813` emits response-level `evidence_labels`, `source_coverage_status`, and `evidence_status`.
- No current legacy route evidence found for a route-level `source_label_taxonomy_version` or compatibility `evidence_envelope`.

### Cockpit route response contract

- `financial-engine_v2/shared/evidence_labels.py:5-35` defines `SOURCE_LABEL_TAXONOMY_VERSION` and the valid source-label taxonomy.
- `financial-engine_v2/backend/app/routes/cockpit_api.py:95-100` imports the shared source-label taxonomy helpers.
- `financial-engine_v2/backend/app/routes/cockpit_api.py:3478-3502` enriches Cockpit UI metadata with `source_label_taxonomy_version`, label counts, response labels, coverage status, and claim-verified counts.
- `financial-engine_v2/backend/app/routes/cockpit_api.py:9965-9983` enforces visible source contracts and applies visible evidence gap labels before returning blocking Cockpit chat responses.
- `financial-engine_v2/backend/app/routes/cockpit_api.py:10005-10034` returns blocking Cockpit chat responses as `{"type": "done", "data": ...}` with `text`, model/latency/cost/source, provider error, action preview, chart, sources, routing metadata, runtime target, and auto-flag metadata.
- `financial-engine_v2/backend/app/routes/cockpit_api.py:10125-10202` streams tool/source/action/chart/done events and terminates with an `event: end` SSE event.

### Current UI callers

- `cockpit-ui/next.config.mjs:50-55` rewrites `/api/:path*` directly to backend `/api/:path*`.
- `cockpit-ui/app/full-chat/page.tsx:6-12` renders the current `ChatScreen`.
- `cockpit-ui/components/cockpit/cockpit-sidebar.tsx:89-92` links the Chat nav item to `/full-chat`.
- `cockpit-ui/lib/api-client.ts:671-684` sends blocking chat to `/api/cockpit/chat`.
- `cockpit-ui/lib/api-client.ts:757-792` sends streaming chat to `/api/cockpit/chat`.
- `cockpit-ui/components/cockpit/chat/chat-screen.tsx:1378-1410` consumes the blocking `sendChatMessage()` path.
- `cockpit-ui/components/cockpit/chat/chat-screen.tsx:1446-1454` consumes the streaming `streamChat()` path.
- `cockpit-ui/lib/marketplace-assistant.ts:861-868` posts marketplace assistant prompts to `/api/cockpit/chat`.
- `cockpit-ui/app/chat/route.ts:17-37` still exposes a Next `/chat` route handler that proxies to backend `/chat`; current audit did not find a current `ChatScreen` caller for it.

### Tests and validation coverage

- `financial-engine_v2/backend/tests/test_chat_route.py:15-76` directly tests the legacy route function for degraded analysis, JSON-safe non-finite payloads, and header session ID use.
- Current audit did not find a legacy route test asserting route-level source-label taxonomy version or a compatibility evidence envelope.
- `financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py:21-60`, `financial-engine_v2/backend/tests/test_cockpit_api_chat_stream_keepalive.py:34-46`, and `financial-engine_v2/backend/tests/test_cockpit_api_chat_sessions.py:29-42` cover Cockpit chat streaming/session behavior.
- `cockpit-ui/lib/api-client.test.ts:49-62` covers frontend streaming transport behavior.

### Parked branch/report evidence

- `reports/agent_jobs/query_legacy_chat_merge_readiness_audit_v1/README.md` classifies prior branch `safe/query-legacy-chat-envelope-compat-v1` at `9fc3d158f0ca` as a clean candidate to harden the legacy chat evidence envelope.
- Current branch containment checks found that `9fc3d158f0ca` is not contained in this audit branch; only the parked `safe/query-legacy-chat-envelope-compat-v1` branch contained it in the current local branch set.
- Current log search found parked/integration candidate commits for legacy chat evidence-envelope work, including `9fc3d158`, `bcdb57dc`, `d86321f7`, `487edc1a`, and `0423e033`, but this audit did not integrate or validate those code changes.

## Confirmed Facts

- `/chat` and `/api/chat` are duplicate mounts of the same legacy route handler.
- `/api/cockpit/chat` is a distinct Cockpit route with a different request/response contract.
- Current Cockpit UI chat clients use `/api/cockpit/chat`, not the legacy backend `/api/chat` route.
- A Next `/chat` proxy still exists and targets backend `/chat`.
- Legacy `chat_with_tenn()` output contains source/evidence labels, but the route wrapper does not expose a versioned route-level evidence envelope.
- Cockpit chat metadata includes `source_label_taxonomy_version` and richer source-label aggregation.

## Inferred Facts

- Route-parity and source-label audits must name the route family they are validating; coverage against `/api/cockpit/chat` does not prove legacy `/chat` or `/api/chat` semantics.
- The Next `/chat` proxy should either be assigned an explicit compatibility/deprecation owner or removed in a separate product change after caller validation.
- The parked legacy evidence-envelope branch remains useful evidence for a future implementation task, but it is not current product behavior.

## DATA_MISSING

- No live HTTP smoke was run for `/chat`, `/api/chat`, or `/api/cockpit/chat`; this audit is repo-evidence only.
- No full transitive frontend caller graph was generated beyond `rg`/file inspection.
- No product decision has been made in this audit to preserve and harden legacy routes versus deprecate them.
- No cherry-pick or semantic validation was run for parked legacy evidence-envelope commits.
- `graphify-out/GRAPH_REPORT.md` was not present in this worktree during earlier preflight context, so no graphify architecture report was used.

## Validation Summary

Planned validation:

- Task-card validation.
- Registry list-active/check-overlap/claim/release.
- Task-card diff check.
- JSON parse checks for generated JSON artifacts.
- `git diff --check`.
- `git diff --cached --check`.

Final command results are recorded in `validation.json` and `diff-check.json`.

## Files Inspected

- `CLAUDE.md`
- `AGENTS.md`
- `docs/architecture/SYSTEM_CONTRACT.md`
- `/home/l4nd0/.claude/projects/-mnt-sdb2-home-l4nd0-tenn/memory/MEMORY.md`
- `financial-engine_v2/backend/app/main.py`
- `financial-engine_v2/backend/app/routes/chat.py`
- `financial-engine_v2/backend/app/services/tenn_chat.py`
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/backend/app/services/query_orchestrator.py`
- `financial-engine_v2/shared/evidence_labels.py`
- `cockpit-ui/next.config.mjs`
- `cockpit-ui/app/chat/route.ts`
- `cockpit-ui/app/full-chat/page.tsx`
- `cockpit-ui/components/cockpit/cockpit-sidebar.tsx`
- `cockpit-ui/components/cockpit/chat/chat-screen.tsx`
- `cockpit-ui/lib/api-client.ts`
- `cockpit-ui/lib/marketplace-assistant.ts`
- `financial-engine_v2/backend/tests/test_chat_route.py`
- `financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py`
- `financial-engine_v2/backend/tests/test_cockpit_api_chat_stream_keepalive.py`
- `financial-engine_v2/backend/tests/test_cockpit_api_chat_sessions.py`
- `cockpit-ui/lib/api-client.test.ts`
- `docs/architecture/19_backend_api_surface.md`
- `financial-engine_v2/README.md`
- `reports/agent_jobs/query_legacy_chat_merge_readiness_audit_v1/README.md`

## Commands Run

- `pwd`
- `date -Iseconds`
- `git rev-parse --show-toplevel`
- `git branch --show-current`
- `git rev-parse HEAD`
- `git status --short --untracked-files=all`
- `git remote -v`
- `git worktree list --porcelain`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap --help`
- `python3 scripts/agent_job_contract.py --help`
- `gh issue view 150 --repo 0rl4nd0l/tenn --json number,title,state,body,labels,url,comments`
- `gh pr list --repo 0rl4nd0l/tenn --state all --search "150 OR legacy chat evidence envelope ownership route parity" --json number,title,state,url,headRefName`
- `rg` searches for chat routes, callers, tests, and parked evidence
- `nl -ba` and `sed` targeted file inspections
- `git branch --contains 9fc3d158f0cab218ae17343c00a56cf4d66cc240`
- `git merge-base HEAD safe/query-legacy-chat-envelope-compat-v1`
- `git diff --name-status HEAD..safe/query-legacy-chat-envelope-compat-v1 -- financial-engine_v2/backend/app/routes/chat.py financial-engine_v2/backend/app/services/tenn_chat.py financial-engine_v2/backend/tests/test_chat_route.py`
- `git log --oneline --decorate --all --grep='legacy chat' --grep='evidence envelope' --grep='taxonomy' --max-count=30`

## Final Status

- Lane: Query Orchestration
- Execution mode: audit_only
- Collision risk: LOW for report-only artifacts; HIGH for route implementation without a separate claim because contested chat/runtime surfaces are involved
- Product behavior changed: no
- Production data access: no
- GPU check: not required
- Recommended PR link text: `Refs #150`
