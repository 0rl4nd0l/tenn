# Cockpit Home Portfolio Aggregation / Day Change v1 Investigation

## Preflight

Lane: Reporting
Branch: preserve/dirty-work-20260430T065748Z
Worktree: /mnt/sdb2/home/l4nd0/tenn
HEAD: 61509ac67319f70997b01b18830a5d831a48b619
Execution mode: AUDIT -> SAFE EXTENSION
Agent: Codex
Task card: docs/agent_tasks/cockpit_home_portfolio_aggregation_v1_20260507.md
Task-card validation: PASS (`python3 scripts/agent_job_contract.py validate ...`)
Registry status: claimed by this Codex session; no competing active jobs before claim; `check-overlap` PASS
Initial dirty state: clean before task card creation; after claim only this task card/report files are dirty
Contested surfaces: financial-engine_v2/backend/app/routes/cockpit_api.py; financial-engine_v2/backend/app/services/cockpit_home.py
Collision risk: controlled MEDIUM

## Contract Gate

Target system layer: Backend Cockpit API/service plus Next.js Cockpit Home BFF presentation.

Relevant contract rules:
- `docs/architecture/SYSTEM_CONTRACT.md` section 1.1: backend is the source of truth.
- `docs/architecture/SYSTEM_CONTRACT.md` section 1.2: Cockpit must call backend APIs for authoritative data reads and must not create alternate financial interpretations.
- `docs/architecture/SYSTEM_CONTRACT.md` sections 2 and 3: no layer skipping, substitution, fabrication, or inference of financial values.
- `docs/architecture/16_currency_and_fx_policy.md`: no current FX conversion path; do not invent rates.

What must not change:
- Holdings remain cockpit-local personal data, not canonical financial truth.
- No total across mixed currencies without deterministic FX support.
- No day-change from current price alone.
- No LLM-generated portfolio values.
- No writes to production data, financial truth, memory, Qdrant, embeddings, extraction, query orchestration, news ingestion, market movers, narrative synthesis, or unrelated tabs.

Why safe if implemented:
- Existing backend holdings enrichment already uses deterministic `quantity * current_price` for market value.
- Existing market price provider already returns `previous_close`; the safe extension is to preserve that field and compute day change only when `quantity`, `current_price`, `previous_close`, and one price currency are all present.
- Existing frontend total guard already withholds totals for missing or mixed currencies; the extension can retain the same guard and add explicit currency display.
- No GPU process or llama-server dependency is involved.

## Confirmed Facts

- `cockpit-ui/lib/cockpit-home-api.ts` builds Home by reading `/api/health`, `/api/cockpit/home/market-session`, `/api/cockpit/holdings`, `/api/commentary/recent`, and `/api/cockpit/home/attention-queue`.
- Home portfolio currently derives totals client-side from `/api/cockpit/holdings`.
- `CockpitHomePortfolioContract` has total, day-change, coverage, and count fields, but no currency field.
- Home UI labels the panel `LOCAL PERSONAL DATA` and says local personal holdings are not canonical financial truth.
- `financial-engine_v2/backend/app/routes/cockpit_api.py` returns holdings with `quantity`, `current_price`, `price_currency`, `price_as_of`, and `market_value`.
- Backend holdings enrichment computes `market_value = quantity * current_price`.
- Backend holdings enrichment withholds unrealized P&L when cost/price currencies are missing or mismatched.
- `MarketPriceProvider.fetch()` returns `current.previous_close`, but holdings enrichment currently drops it.
- No backend `test_cockpit_home_portfolio.py` exists before this task.
- Empty holdings are already safe in the BFF: total 0, day change 0, coverage 100, counts 0/0.

## Inferred Facts

- A backend-owned Home portfolio snapshot is safer than letting the Next BFF be the only aggregation authority.
- The smallest safe backend extension is a read-only portfolio snapshot built from enriched local holdings rows.
- Day-change can be deterministic only for holdings with quantity, current price, previous close, and price currency.
- Day-change coverage should be separate from pricing coverage because a holding can be priced while missing previous close.
- Mixed currencies must block single total and single day-change values unless future FX support is added with date/rate provenance.

## DATA_MISSING

- Actual live personal holdings currency mix was not inspected; task forbids production data access.
- No deterministic FX conversion source was found.
- No persisted previous-close field exists in `holdings_items`; it is available only from the existing price provider response during enrichment.
- No Home browser Playwright spec path is allowed by the task card.

## Subagent Summaries

Subagent A: Home contract/UI audit confirmed Home portfolio is a Next BFF aggregate from `/api/cockpit/holdings`, holdings are labelled local personal data, day change is unavailable for non-empty holdings, and total aggregation already blocks mixed/missing price currencies. Gaps: no portfolio currency field and no backend Home portfolio test.

Subagent B: Backend holdings/pricing audit confirmed `GET /api/cockpit/holdings` is backed by cockpit-local `holdings_items`, enriched with live price/current market value. Provider has `previous_close`; no FX source is safe. Recommended backend-owned portfolio snapshot with explicit local-personal-data source label, counts, coverage, currency, total, day change, and missing signals.

Subagent C: Collision/test/browser audit confirmed only this task-card file was dirty, registry has only this Codex claim, and backend `cockpit_api.py` remains contested. It recommended focused frontend/backend tests, `git diff --check`, task-card `check-diff`, and browser checks without adding new Playwright files outside the allowlist.

## Candidate Source Table

| Source | Current fields | Use | Decision |
| --- | --- | --- | --- |
| `holdings_items` via `StateStore.list_holdings()` | ticker, quantity, avg_cost, cost_currency, status, updated_at | local personal holdings count and quantity | Use as local personal data only |
| `_enrich_holdings_with_live_prices()` | current_price, price_currency, price_as_of, market_value, unrealized_pnl, valuation_warning | pricing coverage and market value | Use existing deterministic fields |
| `MarketPriceProvider.fetch()` | current.price, current.previous_close, market_time, currency, history | day-change basis | Preserve `previous_close`; compute only when present |
| FX policy / FX sources | no current deterministic FX conversion | mixed-currency conversion | Do not use; keep ambiguous |
| Portfolio analysis modules | equal-weight/analysis fallback behavior | not local holdings truth | Do not use |

## Portfolio Field Decision Table

| Field | Safe source | Output rule |
| --- | --- | --- |
| `holdings_count` | enriched holdings row count | Always deterministic |
| `priced_holdings_count` | rows with `market_value` and `price_currency` | Always deterministic |
| `coverage_percent` | priced/total count | Empty holdings: 100; otherwise rounded percent |
| `currency` | single price currency among priced holdings | Null if no priced holdings, missing currencies, or mixed currencies |
| `total_value` | sum of same-currency market values | Null if missing/mixed currency; 0 for empty holdings |
| `day_change` | sum of `quantity * (current_price - previous_close)` in same currency | Null unless all day-change-capable rows share one currency and at least one eligible holding exists; 0 for empty holdings |
| `day_change_percent` | `day_change / prior_value * 100` | Null unless prior value is positive; 0 for empty holdings |
| `day_change_priced_holdings_count` | rows with full day-change inputs | Always deterministic |
| `as_of` | latest price timestamp | Null only if no timestamps; now for empty snapshot only if needed |
| `data_missing` | deterministic guard reasons | Include currency ambiguity, missing price coverage, and day-change unavailable/partial reasons |

## Go/No-Go Decision

Decision: GO for SAFE EXTENSION.

Reason:
- Registry overlap is clear.
- Current dirtiness is owned by this task.
- The deterministic inputs exist for total and day-change when same-currency priced holdings are available.
- The implementation can remain inside allowed files.
- Missing or mixed-currency conditions can remain explicit `PARTIAL` states.

## Files To Touch

- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/backend/app/services/cockpit_home.py`
- `financial-engine_v2/backend/tests/test_cockpit_home_portfolio.py`
- `cockpit-ui/types/cockpit-home.ts`
- `cockpit-ui/lib/cockpit-home-api.ts`
- `cockpit-ui/lib/cockpit-home-api.test.ts`
- `cockpit-ui/components/cockpit/home/home-page.tsx`
- `reports/agent_jobs/cockpit_home_portfolio_aggregation_v1_20260507/README.md`
- `reports/agent_jobs/cockpit_home_portfolio_aggregation_v1_20260507/diff-check.json`

## Collision Risk

Controlled MEDIUM.

Rationale: implementation touches contested backend Cockpit route/service files, but the shared registry shows no competing job, the worktree has no unrelated dirty overlap, and the patch is additive/read-only for local holdings/Home portfolio surfaces.
