# Route Ownership Matrix

| Route | Current owner | Current consumer evidence | Evidence-label state | Taxonomy/envelope state | Decision |
| --- | --- | --- | --- | --- | --- |
| `POST /chat` | `financial-engine_v2/backend/app/routes/chat.py` legacy backend route | Mounted by `main.py` without prefix; documented in backend API surface | Receives labels from `chat_with_tenn()` response content | No route-level taxonomy version or versioned compatibility envelope found in current branch | Keep open for keep-vs-retire decision |
| `POST /api/chat` | Same `routes/chat.py` handler via `chat_router` mounted with `prefix="/api"` | Mounted by `main.py`; documented as intentional compatibility exposure | Same as `/chat` | Same as `/chat` | Keep open for keep-vs-retire decision |
| `POST /api/cockpit/chat` | `financial-engine_v2/backend/app/routes/cockpit_api.py` Cockpit route | `cockpit-ui/lib/api-client.ts` blocking and SSE methods target this route | Uses Cockpit visible-source and UI metadata path | Emits source label taxonomy metadata through Cockpit route helpers | Current Cockpit web chat owner |

## Current Classification

- Legacy API route: `/chat` and `/api/chat`.
- Cockpit web route: `/api/cockpit/chat`.
- Validation implication: a test that exercises `/api/cockpit/chat` does not prove the legacy route contract, and a test that exercises `/api/chat` does not prove the Cockpit web route contract.

## Parked Work

Prior audit `query_legacy_chat_merge_readiness_audit_v1` identified commit `9fc3d158f0cab218ae17343c00a56cf4d66cc240` on branch `safe/query-legacy-chat-envelope-compat-v1` as relevant legacy-envelope compatibility work. Current branch containment check found only that safe branch contains the commit.
