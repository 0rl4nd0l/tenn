# Cockpit Home Attention Queue v1

## Branch / HEAD

- Branch: `preserve/dirty-work-20260430T065748Z`
- Preflight HEAD: `8925498e5f9bcfdd6a90a35d20093ce0cd23a689`
- Lane: Reporting
- Execution mode: AUDIT -> SAFE EXTENSION
- Collision risk: controlled MEDIUM, because `financial-engine_v2/backend/app/routes/cockpit_api.py` is a contested surface.

## Task Card Path

- `docs/agent_tasks/cockpit_home_attention_queue_v1_20260507.md`
- Validation: `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_home_attention_queue_v1_20260507.md` returned `ok: true`.
- Diff check: `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_home_attention_queue_v1_20260507.md` returned `ok: true`; changed files were allowed.

## Registry / Lock Status

- Registry root: `.git/tenn-agent-registry`
- Scope: shared
- Pre-implementation `list-active`: no active jobs with Reporting/Home overlap.
- Pre-implementation `check-overlap`: `ok: true`.
- Claim: `cockpit_home_attention_queue_v1_20260507`
- Release: `python3 scripts/agent_job_registry.py release cockpit_home_attention_queue_v1_20260507` returned `ok: true` and removed the active record.
- Post-release `list-active`: `active_jobs: []`.

## Preflight Summary

- `git status --short --untracked-files=all` was clean before the task card was created.
- `git worktree list` showed multiple sibling worktrees, so implementation was treated as live-repo work.
- Relevant recent commits included:
  - `8925498 milestone(reporting): wire cockpit home market session`
  - `3d49c9d milestone(reporting): record cockpit home final integration readiness`
  - `6781f89 milestone(reporting): record cockpit home bff route integration`
- `python` was not available on PATH; repo-supported scripts were run with `python3`.
- System contract scope: frontend BFF and backend presentation API only. No financial truth, extraction, memory, Qdrant, embeddings, or query routing surfaces were changed.

## Subagent Reports Summary

- Home contract/UI audit: attention queue had item-level contract support but no backend endpoint. The BFF emitted `NO_ATTENTION_QUEUE_ENDPOINT`, and the UI could render real items once a queue-level state was added.
- Backend/local source audit: queued market-update followups were the safest local/backend-owned source. They are deterministic operational state with stable IDs, status, timestamps, and no production mutation requirement.
- Collision/test audit: collision risk stayed controlled MEDIUM because only the Cockpit Home route/service and UI Home files were touched. Focused frontend, backend, task-card, diff, and browser checks were required.

## Candidate Source Table

| Candidate | Deterministic | Stable IDs | Local/backend-owned | Decision |
| --- | --- | --- | --- | --- |
| Queued market-update followups | Yes | Yes, `followup_id` | Yes | Chosen for v1 |
| Cockpit flagged reports | Yes | Yes | Evaluation artifact | Not chosen; outside Home operational queue v1 scope |
| Extraction review queue | Likely | DATA_MISSING | Financial truth adjacent | Not chosen |
| Marketplace alerts | DATA_MISSING | DATA_MISSING | DATA_MISSING | Not chosen |
| Recent commentary gaps | Partial | Partial | Provenance/reporting | Not chosen |

## Go/No-Go Decision

GO. The implementation uses existing local Cockpit operational state from `StateStore.list_market_update_followups(status="queued")`. Queue items are not LLM-generated and do not create financial-truth claims. Empty queues are valid `READY` responses.

## Files Changed

- `docs/agent_tasks/cockpit_home_attention_queue_v1_20260507.md`
- `reports/agent_jobs/cockpit_home_attention_queue_v1_20260507/INVESTIGATION.md`
- `reports/agent_jobs/cockpit_home_attention_queue_v1_20260507/README.md`
- `reports/agent_jobs/cockpit_home_attention_queue_v1_20260507/diff-check.json`
- `reports/agent_jobs/cockpit_home_attention_queue_v1_20260507/status.json`
- `financial-engine_v2/backend/app/services/cockpit_home.py`
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/backend/tests/test_cockpit_home_attention_queue.py`
- `cockpit-ui/types/cockpit-home.ts`
- `cockpit-ui/lib/cockpit-home-api.ts`
- `cockpit-ui/lib/cockpit-home-api.test.ts`
- `cockpit-ui/lib/cockpit-home-contract.test.ts`
- `cockpit-ui/components/cockpit/home/home-page.tsx`
- `cockpit-ui/components/cockpit/home/cards/attention-queue-card.tsx`

## Tests / Lint / Type / Browser Validation

- Backend focused: `cd financial-engine_v2 && .venv/bin/python -m pytest backend/tests/test_cockpit_home_attention_queue.py -q` -> `3 passed in 4.97s`.
- Backend combined Home: `cd financial-engine_v2 && .venv/bin/python -m pytest backend/tests/test_cockpit_home_market_session.py backend/tests/test_cockpit_home_attention_queue.py -q` -> `6 passed in 2.98s`.
- Backend lint: `cd financial-engine_v2 && .venv/bin/python -m ruff check backend/app/services/cockpit_home.py backend/app/routes/cockpit_api.py backend/tests/test_cockpit_home_attention_queue.py` -> `All checks passed!`.
- Frontend focused: `cd cockpit-ui && pnpm exec vitest run lib/cockpit-home-api.test.ts lib/cockpit-home-contract.test.ts` -> `2 passed`, `15 tests passed`, duration `6.85s`.
- TypeScript: `cd cockpit-ui && npx tsc --noEmit --pretty false` -> exit 0, no output.
- ESLint: `cd cockpit-ui && pnpm exec eslint app/api/cockpit/home/route.ts lib/cockpit-home-api.ts lib/cockpit-home-contract.ts types/cockpit-home.ts components/cockpit/home --max-warnings=0` -> exit 0, no output.
- Diff whitespace: `git diff --check` -> exit 0, no output.
- Backend live endpoint: `curl -sS -i -m 4 http://127.0.0.1:8000/api/cockpit/home/attention-queue` -> HTTP 200, `data_state: READY`, 50 local queued followup items.
- BFF live endpoint: `curl -sS http://127.0.0.1:3107/api/cockpit/home` -> `attention_queue_state.data_state: READY`, `attention_count: 50`.
- Browser validation: Playwright against `http://127.0.0.1:3107/` passed these checks: page status 200, `/api/cockpit/home` requested, Home rendered through BFF, `NO_ATTENTION_QUEUE_ENDPOINT` absent, attention queue visible, unsupported states visible, no mock fixture text, no exact `/chat` or `/api/chat` requests, nested buttons count 0.
- Browser note: Next dev console emitted an existing hydration mismatch warning on root `html` color-scheme attributes. The focused Home checks still passed.

## What Is Now Live

- Backend endpoint: `GET /api/cockpit/home/attention-queue`.
- BFF wiring: Cockpit Home calls the backend attention queue endpoint and includes `attention_queue_state`.
- UI behavior: queued local market-update followups render as operational attention items with stable IDs, status, source type, reason, priority, and timestamps when available.
- Empty queue behavior: covered by backend tests and treated as `READY` with no items, not as an error.

## What Remains DATA_MISSING And Why

- Market movers remain `DATA_MISSING` because no deterministic Home market-movers endpoint was introduced.
- Home narrative remains `DATA_MISSING` because no narrative synthesis endpoint was introduced.
- Portfolio total/day-change remain partially missing where backend holdings data lacks deterministic aggregate currency/day-change fields.
- Recent commentary remains missing when the backend returns no approved, resolvable commentary sources.

## Collision Risks

- `financial-engine_v2/backend/app/routes/cockpit_api.py` is a contested surface; edits were limited to adding the Home attention queue response models and route.
- No active registry overlap remained after release.
- No unrelated Cockpit tabs, query routing, source resolver, memory, extraction, parser, Qdrant, embeddings, or financial-truth files were touched.

## DATA_MISSING

- No production-data validation was performed; task card explicitly requires `production_data_access: false`.
- Browser validation used local state with 50 queued market-update followups. Empty queue browser behavior was not observed live, but it is covered by focused backend and BFF tests.
- The root `html` hydration warning source was not investigated because it is outside the allowed mutation scope.

## Final Git Status

After the final milestone commit for this task, `git status --short --untracked-files=all` is expected to return no task-related dirty files. The terminal closeout records the observed final status.

## Project Memory Save Recommendation

Save that Cockpit Home Attention Queue v1 is wired to existing queued market-update followups through `GET /api/cockpit/home/attention-queue`, with empty queues represented as `READY` and unresolved/non-deterministic Home sections kept explicit as `DATA_MISSING`.
