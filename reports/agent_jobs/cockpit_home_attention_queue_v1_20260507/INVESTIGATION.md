# Cockpit Home Attention Queue v1 Investigation

## Confirmed Facts

- Branch: `preserve/dirty-work-20260430T065748Z`.
- HEAD at preflight: `8925498e5f9bcfdd6a90a35d20093ce0cd23a689`.
- Initial `git status --short --untracked-files=all` was clean before the task card was created.
- Relevant recent commits include `8925498 milestone(reporting): wire cockpit home market session`, `3d49c9d milestone(reporting): record cockpit home final integration readiness`, and `6781f89 milestone(reporting): record cockpit home bff route integration`.
- Task card path: `docs/agent_tasks/cockpit_home_attention_queue_v1_20260507.md`.
- Task-card validation passed with `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_home_attention_queue_v1_20260507.md`.
- Registry overlap check passed with no issues for this task card.
- The task is claimed in the shared registry as `cockpit_home_attention_queue_v1_20260507`.
- Current Home BFF calls `/api/health`, `/api/cockpit/home/market-session`, `/api/cockpit/holdings`, and `/api/commentary/recent?limit=5`.
- Current Home BFF creates attention queue state via `NO_ATTENTION_QUEUE_ENDPOINT` and a `DATA_MISSING` placeholder item.
- `financial-engine_v2/cockpit/storage/state.py` defines `market_update_followups` as cockpit-local report follow-up action state, not authoritative financial data.
- `market_update_followups` rows have `followup_id`, `report_id`, optional `ticker`, `action_type`, `priority_score`, `reason`, `status`, and `created_at`.
- `StateStore.list_market_update_followups(status="queued")` can expose queued follow-up rows without mutating local state.

## Inferred Facts

- A read-only Home endpoint backed only by `market_update_followups` is a safe extension because it exposes existing cockpit-local operational state and does not create a new source of financial truth.
- Empty queued follow-ups should be represented as `READY` with an empty item list, not `DATA_MISSING`.
- A queued market-update follow-up can be displayed as an attention item using deterministic fields already in the row: `followup_id`, `ticker`, `action_type`, `priority_score`, `reason`, `status`, and `created_at`.
- The current frontend needs a queue-level state in addition to item-level state so empty-ready is representable.

## DATA_MISSING

- Live local `~/.financial_engine_cockpit/state.db` contents were not treated as truth for implementation; the contract is based on repo code and tests.
- No Home-safe endpoint exists yet for open flagged reports, ops jobs, pending commentary transcripts, marketplace alerts, extraction review items, or thesis alerts under this task's allowed mutation scope.
- No source-detail route is proven for `market_update_followups`, so attention items must not claim a resolvable source handoff.
- No deterministic day-change, market-movers, session-summary, theme-candidates, or tomorrow-prep source is added by this task.

## Subagent Summaries

- Subagent A found that `CockpitHomeAttentionItemContract` is item-level only and the BFF currently emits `NO_ATTENTION_QUEUE_ENDPOINT`. It also found that the UI can render real queue items but currently collapses attention section state to `PARTIAL` or `DATA_MISSING`, making empty-ready ambiguous.
- Subagent B found multiple deterministic operational candidates. It identified open flagged reports, ops jobs, pending commentary transcripts, marketplace alerts, extraction review queues, thesis alerts, and market-update followups as possible sources. This implementation chooses only market-update followups because the source is already in cockpit-local `StateStore`, has stable queue IDs and statuses, and can be exposed with a minimal backend route inside allowed files.
- Subagent C found collision risk `MEDIUM, controlled`: `cockpit_api.py` is contested, but this task owns it through the active registry claim and no overlapping active job was present for Reporting/Home files. It supplied the focused frontend, backend, general, task-card, and browser validation commands.

## Candidate Source Table

| Candidate | Deterministic | Local/operational | Stable IDs | Timestamps/status/priority | Within allowed implementation scope | Decision |
|---|---:|---:|---:|---:|---:|---|
| `market_update_followups` in `StateStore` | Yes | Yes | `followup_id` | `created_at`, `status`, `priority_score` | Yes | GO |
| Open flagged reports | Yes | Yes | `report_id` | `saved_at`, resolution status, findings severity | No focused service file allowed for clean aggregation | Defer |
| Ops jobs | Yes | Yes | `job_id` | queued/started/updated/completed, status, counts | Existing ops route outside Home contract | Defer |
| Pending commentary transcripts | Yes | Yes | `source_id` | staged metadata, pending state | Existing commentary API outside Home route | Defer |
| Marketplace alerts | Yes | Yes | `alert_id` | created/updated/status | Marketplace surfaces are contested and out of this narrow Home queue source set | Defer |
| Extraction review queue | Yes | QA state | run/session/error IDs | review status/timestamps | Touches financial QA surfaces; not needed for v1 | Defer |
| Thesis proposals/alerts | Yes | Personal memory | proposal/alert IDs | status/timestamps/severity | Memory boundary; out of task hard boundaries | No-go |
| TradingView alerts | Partial | Operational | no stable native item contract | missing status/severity | Insufficient for v1 | No-go |

## Chosen Contract

Backend endpoint:

- `GET /api/cockpit/home/attention-queue`
- Read-only.
- Source: `CockpitService.get_instance().state_store.list_market_update_followups(status="queued", limit=...)`.
- Empty queue returns `READY`, `degraded=false`, `data_missing=[]`, and `items=[]`.
- Backend failures return HTTP 503; the BFF maps this to `DATA_MISSING`.

Frontend Home BFF contract:

- Add `attention_queue_state: CockpitHomeDeterministicState`.
- Keep `attention_queue: CockpitHomeAttentionItemContract[]`.
- Map endpoint rows into ready operational-trace items with non-resolvable evidence.
- Preserve `NO_ATTENTION_QUEUE_ENDPOINT` only when the backend endpoint is unavailable.

## Implementation Go/No-Go

GO.

The source is deterministic, local cockpit operational state. No production data mutation is required. Stable IDs are available from `followup_id`. The implementation fits inside allowed files and does not touch extraction, financial truth storage, memory stores, Qdrant, embeddings, news ingestion, query orchestration, parser routing, gold labels, source detail resolver, market movers, or narrative synthesis.

## Files To Touch

- `financial-engine_v2/backend/app/services/cockpit_home.py`
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/backend/tests/test_cockpit_home_attention_queue.py`
- `cockpit-ui/types/cockpit-home.ts`
- `cockpit-ui/lib/cockpit-home-api.ts`
- `cockpit-ui/lib/cockpit-home-api.test.ts`
- `cockpit-ui/lib/cockpit-home-contract.test.ts`
- `cockpit-ui/components/cockpit/home/home-page.tsx`
- `cockpit-ui/components/cockpit/home/cards/attention-queue-card.tsx`
- `reports/agent_jobs/cockpit_home_attention_queue_v1_20260507/README.md`
- `reports/agent_jobs/cockpit_home_attention_queue_v1_20260507/diff-check.json`

## Collision Risk

Controlled MEDIUM.

`financial-engine_v2/backend/app/routes/cockpit_api.py` is a contested surface, but this task has an active registry claim and current overlap check reports no issue. The route change is additive, narrow, and adjacent to the existing Home market-session endpoint.
