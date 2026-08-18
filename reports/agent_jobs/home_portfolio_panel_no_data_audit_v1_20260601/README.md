# Home Portfolio Panel No-Data Audit

Issue: #86, `[Cockpit] Home portfolio panel shows no data`

## Decision

Keep #86 open as `DATA_MISSING` / needs runtime reproduction. Do not implement
in this pass because the likely product files overlap active draft PRs.

## Current Evidence

- Shared branch is live and the shared checkout has an active Financial Truth
  job on extraction files. This audit ran in an isolated worktree.
- No matching open PR was found for the exact #86 portfolio panel root cause.
- PR #134 already touches `cockpit-ui/components/cockpit/home/home-page.tsx`
  and `cockpit-ui/lib/cockpit-home-api.test.ts`.
- PR #159 already touches `financial-engine_v2/backend/app/routes/cockpit_api.py`
  and `financial-engine_v2/backend/app/services/cockpit_home.py`.
- Local backend health at `127.0.0.1:8000/api/health` returned `status: ok`.
- Redacted backend portfolio summary from
  `127.0.0.1:8000/api/cockpit/home/portfolio` returned:
  - `ok: true`
  - `data_state: PARTIAL`
  - `holdings_count: 78`
  - `priced_holdings_count: 78`
  - `day_change_priced_holdings_count: 77`
  - `coverage_percent: 100`
  - `total_value` is null
  - `currency` is null
  - `data_missing_codes`: `PORTFOLIO_TOTAL_CURRENCY_AMBIGUOUS`,
    `PORTFOLIO_DAY_CHANGE_CURRENCY_AMBIGUOUS`
- A temporary isolated Next.js dev server was started against the same backend
  and `127.0.0.1:3000/api/cockpit/home` returned a redacted BFF portfolio
  summary with the same partial state:
  - `data_state: PARTIAL`
  - `holdings_count: 78`
  - `priced_holdings_count: 78`
  - `coverage_percent: 100`
  - `total_value` is null
  - `currency` is null
  - `data_missing_codes`: `PORTFOLIO_TOTAL_CURRENCY_AMBIGUOUS`,
    `PORTFOLIO_DAY_CHANGE_CURRENCY_AMBIGUOUS`
- A headless browser text inspection of the Home portfolio panel showed:
  `Total Value DATA_MISSING`, `Day Change DATA_MISSING`, `Coverage 100%`,
  `78/78 priced`, and both currency-ambiguity signals.

No holding rows, tickers, account details, local paths, or raw personal
portfolio values are committed in this report.

## Interpretation

The backend and BFF portfolio payloads are not empty in the current local
runtime. They return a partial state with holdings present, but no aggregate
total because the deterministic priced holdings do not share one currency. The
Home panel renders this as `DATA_MISSING` headline values plus coverage and
currency-ambiguity signals. The likely product gap is partial-state clarity:
the panel can look like "no data" even though holdings and coverage evidence are
present.

## Safe Next Step

Use a follow-up isolated task after PR #134 and PR #159 are merged or parked.
Fix only the proven gap:

- frontend empty/partial-state clarity if the payload is present but unclear;
- backend portfolio aggregation/status semantics if the BFF receives an
  unsupported or misleading contract;
- no product change if reviewers decide the current `DATA_MISSING` headline is
  the intended representation for a multi-currency partial portfolio.
