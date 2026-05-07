# Cockpit Home Portfolio Aggregation / Day Change v1

## Summary

Branch: preserve/dirty-work-20260430T065748Z
Starting HEAD: 61509ac67319f70997b01b18830a5d831a48b619
Final commit subject: milestone(reporting): wire cockpit home portfolio snapshot
Active task card: docs/agent_tasks/cockpit_home_portfolio_aggregation_v1_20260507.md
Registry claim: claimed by Codex during implementation, then released; final `list-active` returned no active jobs
Lane: Reporting
Supporting lane: Provenance
Execution mode: AUDIT -> SAFE EXTENSION
Collision risk: controlled MEDIUM
Production data access: false

## Preflight

- Task card was created from the supplied content and validated with `python3 scripts/agent_job_contract.py validate ...`: PASS.
- `python3 scripts/agent_job_registry.py list-active` before claim returned no active jobs.
- `python3 scripts/agent_job_registry.py check-overlap ...` returned PASS before claim and again before implementation.
- Claim succeeded under shared registry root `/mnt/sdb2/home/l4nd0/tenn/.git/tenn-agent-registry`.
- Initial worktree status was clean before task-card creation.
- `cockpit_api.py` and `cockpit_home.py` were treated as contested surfaces; no competing lock or dirty overlap was found.

## Subagent Summary

- Subagent A confirmed Home portfolio was derived from `/api/cockpit/holdings`, had no currency field, labelled holdings as local personal data, and kept non-empty day change as unavailable.
- Subagent B confirmed the backend holdings route has deterministic market-value inputs and the price provider already returns `previous_close`; no safe FX source exists.
- Subagent C confirmed only this task card was dirty during audit, no competing registry job existed, and browser validation should avoid adding Playwright files outside the allowlist.

## Candidate Sources

| Source | Decision |
| --- | --- |
| `holdings_items` via `StateStore.list_holdings()` | Use only as cockpit-local personal data. |
| `_enrich_holdings_with_live_prices()` | Use deterministic `current_price`, `price_currency`, `price_as_of`, `market_value`; now preserves `previous_close`. |
| `MarketPriceProvider.fetch()` | Use existing `current.previous_close` for day-change only when present. |
| FX conversion | DATA_MISSING; no deterministic FX source found. |
| Portfolio analysis modules | Not used; fallback/equal-weight behavior is unsafe for this contract. |

## Field Decisions

| Field | Result |
| --- | --- |
| `total_value` | Sum priced holdings only when all priced holdings have one known currency. |
| `currency` | Returned only for a single known price currency. |
| `coverage_percent` | Deterministic priced/total holdings coverage; empty holdings = 100. |
| `day_change` | Sum `quantity * (current_price - previous_close)` only for same-currency deterministic rows; partial coverage is labelled. |
| `day_change_percent` | Computed against covered previous-close value only when positive. |
| Mixed currencies | `PORTFOLIO_TOTAL_CURRENCY_AMBIGUOUS`; no total or day-change value. |
| Missing day-change basis | `PORTFOLIO_DAY_CHANGE_UNAVAILABLE` or `PORTFOLIO_DAY_CHANGE_PARTIAL`. |

## Go/No-Go

Decision: GO for SAFE EXTENSION.

Rationale: deterministic inputs exist in existing backend holdings/pricing paths; the implementation is read-only for local holdings, blocks mixed currencies, avoids FX, labels portfolio data as `local_personal_data`, and stays inside allowed files.

## Files Changed

- `docs/agent_tasks/cockpit_home_portfolio_aggregation_v1_20260507.md`
- `reports/agent_jobs/cockpit_home_portfolio_aggregation_v1_20260507/INVESTIGATION.md`
- `reports/agent_jobs/cockpit_home_portfolio_aggregation_v1_20260507/README.md`
- `reports/agent_jobs/cockpit_home_portfolio_aggregation_v1_20260507/diff-check.json`
- `reports/agent_jobs/cockpit_home_portfolio_aggregation_v1_20260507/status.json`
- `cockpit-ui/types/cockpit-home.ts`
- `cockpit-ui/lib/cockpit-home-api.ts`
- `cockpit-ui/lib/cockpit-home-api.test.ts`
- `cockpit-ui/components/cockpit/home/home-page.tsx`
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/backend/app/services/cockpit_home.py`
- `financial-engine_v2/backend/tests/test_cockpit_home_portfolio.py`

## Validation

- `financial-engine_v2/.venv/bin/python -m pytest backend/tests/test_cockpit_home_portfolio.py -q`: PASS, 6 passed.
- `financial-engine_v2/.venv/bin/python -m pytest backend/tests/test_cockpit_home_market_session.py backend/tests/test_cockpit_home_attention_queue.py backend/tests/test_cockpit_home_portfolio.py -q`: PASS, 12 passed.
- `financial-engine_v2/.venv/bin/python -m ruff check backend/app/services/cockpit_home.py backend/app/routes/cockpit_api.py backend/tests/test_cockpit_home_portfolio.py`: PASS.
- `pnpm exec vitest run lib/cockpit-home-api.test.ts lib/cockpit-home-contract.test.ts`: PASS, 2 files / 16 tests.
- `npx tsc --noEmit --pretty false`: PASS.
- `pnpm exec eslint app/api/cockpit/home/route.ts lib/cockpit-home-api.ts lib/cockpit-home-contract.ts types/cockpit-home.ts components/cockpit/home --max-warnings=0`: PASS.
- `git diff --check`: PASS.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_home_portfolio_aggregation_v1_20260507.md`: BLOCKED by unrelated dirty news-pipeline files outside this task card (`financial-engine_v2/backend/app/services/news_memo_extractor.py`, `financial-engine_v2/backend/app/tasks/news_tasks.py`, `financial-engine_v2/backend/tests/test_news_memo_extractor.py`, `financial-engine_v2/backend/tests/test_news_tasks.py`, `scripts/load_news_to_qdrant.py`). The Home file itself was added explicitly to the task card because the contract checker uses exact allowed-file matching while the registry supports the original `cockpit-ui/components/cockpit/home/**` glob.

## Browser Validation

Environment:
- Backend: isolated patched backend on `http://127.0.0.1:8010`, with `DATA_ROOT=/tmp/tenn-home-portfolio-data` and `COCKPIT_STATE_DB=/tmp/tenn-home-portfolio-cockpit-state.db`.
- Next UI: `http://127.0.0.1:8081`, with `NEXT_PUBLIC_API_URL=http://127.0.0.1:8010`.

Results:
- `GET /api/cockpit/home`: 200.
- `/` rendered through Home BFF.
- Portfolio panel rendered `LOCAL PERSONAL DATA` and "not canonical financial truth".
- Empty local holdings rendered READY portfolio state with total 0, day-change 0, coverage 100, and counts `0/0`.
- Unsupported sections remained visible as DATA_MISSING.
- No mock fixture text was present.
- No exact `/chat` or `/api/chat` request fired during Home render.
- Nested button selector count was 0.
- Residual dev warning: one existing Next/React hydration mismatch warning on the root `<html>` style attribute; not introduced by this patch and nested button count remained 0.

## What Is Live

- Backend exposes `GET /api/cockpit/home/portfolio` as a backend-owned local personal portfolio snapshot.
- Holdings enrichment preserves `previous_close` and per-holding day-change fields when the existing price provider supplies deterministic inputs.
- Home BFF consumes `/api/cockpit/home/portfolio` instead of aggregating portfolio totals from holdings rows itself.
- Home portfolio contract now includes `source_label`, `currency`, and `day_change_priced_holdings_count`.
- Home UI formats total/day-change with the returned currency and shows day-change coverage.

## DATA_MISSING

- Actual live personal holdings currency mix was not inspected because production data access is false.
- FX conversion remains unavailable; mixed-currency totals stay ambiguous.
- Browser validation used empty isolated local holdings, so deterministic non-empty totals and mixed-currency labels are covered by focused tests rather than live personal data.
- Home Playwright spec creation remains out of scope because `cockpit-ui/tests/**` is outside the task-card allowlist.

## Remaining Risks

- Live `:8000` backend was running older code during validation; browser validation used a separate patched isolated backend on `:8010`.
- Existing Next dev hydration warning remains visible in browser console.
- Day-change is only as current as the existing price provider snapshot; no additional stale-price policy was introduced in this v1.

## Final Status

Final git status after milestone commit:
- Task-owned files are committed in the closeout milestone commit.
- Registry status file records `released`; final `python3 scripts/agent_job_registry.py list-active` returned no active jobs.
- Unrelated dirty files outside this task remain in the news-pipeline lane and were not touched or staged by this task: `financial-engine_v2/backend/app/services/news_memo_extractor.py`, `financial-engine_v2/backend/app/tasks/news_tasks.py`, `financial-engine_v2/backend/tests/test_news_memo_extractor.py`, `financial-engine_v2/backend/tests/test_news_tasks.py`, `scripts/load_news_to_qdrant.py`, `scripts/test_load_news_qdrant_preflight.py`.
- Generated `cockpit-ui/next-env.d.ts` dev-server change was reverted because it is outside the allowlist.

Project Memory save recommendation:
- Save that Cockpit Home portfolio is now backend-owned through `/api/cockpit/home/portfolio`, remains `local_personal_data`, blocks mixed-currency totals without FX, and treats day-change as deterministic only with current price, previous close, quantity, and currency.
