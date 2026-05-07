# Cockpit Home BFF Route v1 Report

## 1. Branch / HEAD / Worktree / Dirty Status

- Branch: `safe/cockpit-home-bff-route-v1`
- HEAD: `c5ef4f853596`
- Worktree: `/mnt/sdb2/home/l4nd0/tenn-cockpit-home-bff-route-v1`
- Base: `c5ef4f8535961a9411255a252857b2b6f22ee2f9` (`docs(evaluation): classify dirty preserve worktree after cockpit home contract`)
- Initial isolated-worktree status before task-card creation: clean
- Final dirty status: allowed added files only

## 2. Task Card and Registry Status

- Task card: `docs/agent_tasks/cockpit_home_bff_route_v1.md`
- Validation: `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_home_bff_route_v1.md` passed with `"ok": true`
- Shared registry preflight: `list-active --repo-root /mnt/sdb2/home/l4nd0/tenn` returned no active jobs on retry
- Overlap check: `check-overlap ... --repo-root /mnt/sdb2/home/l4nd0/tenn-cockpit-home-bff-route-v1` passed with `"ok": true`
- Claim: created successfully for `cockpit_home_bff_route_v1`
- Release: performed after final validation

Note: the exact task-card command using `--repo-root /mnt/sdb2/home/l4nd0/tenn` cannot find an isolated-worktree-only task card by relative path. The shared-registry overlap check was therefore rerun against the isolated worktree root while still resolving the same shared registry under `/mnt/sdb2/home/l4nd0/tenn/.git/tenn-agent-registry`.

## 3. Files Changed

- `docs/agent_tasks/cockpit_home_bff_route_v1.md`
- `cockpit-ui/app/api/cockpit/home/route.ts`
- `cockpit-ui/lib/cockpit-home-api.ts`
- `cockpit-ui/lib/cockpit-home-api.test.ts`
- `reports/agent_jobs/cockpit_home_bff_route_v1/README.md`
- `reports/agent_jobs/cockpit_home_bff_route_v1/diff-check.json`
- `reports/agent_jobs/cockpit_home_bff_route_v1/status.json`

## 4. Route Contract Implemented

Added `GET /api/cockpit/home` as a narrow Next.js BFF route. The route:

- runs in `nodejs`
- forwards browser headers through `copyRequestHeaders`
- returns `CockpitHomeBffResponse`
- sets `Cache-Control: no-store`
- delegates assembly to `buildCockpitHomeBffResponse`

The helper returns a contract-shaped response with top-level `data_state`, `degraded`, `data_missing`, `generated_at`, and `source_label_taxonomy_version`.

## 5. Upstream Surfaces Used or Intentionally Not Used

Used:

- `GET /api/health` for backend liveness data-health state
- `GET /api/cockpit/holdings` for cockpit-local personal holdings summary only
- `GET /api/commentary/recent?limit=5` for backend-resolvable approved commentary source identities

Intentionally not used:

- legacy `/chat`
- backend runtime code changes
- Postgres, Qdrant, filings, embeddings, news stores, memory stores, or local production files
- ingestion, reindex, resync, or long-running jobs
- Home UI page wiring

## 6. DATA_MISSING / Degraded Semantics

Implemented deterministic `DATA_MISSING` for Home sections that do not yet have dedicated backend surfaces:

- market session
- market movers
- attention queue
- session summary
- theme candidates
- tomorrow prep

Implemented degraded/DATA_MISSING upstream behavior:

- backend liveness failure becomes `BACKEND_HEALTH_UNAVAILABLE`
- holdings failure becomes `HOLDINGS_ENDPOINT_UNAVAILABLE`
- commentary recent failure becomes `COMMENTARY_RECENT_UNAVAILABLE`
- empty commentary recent response becomes `NO_RECENT_COMMENTARY`
- commentary rows missing `source_id` become `RECENT_COMMENTARY_SOURCE_ID_MISSING`

Portfolio-specific safeguards:

- holdings are treated as cockpit-local personal data, not financial truth
- no day-change values are fabricated; missing day-change becomes `PORTFOLIO_DAY_CHANGE_UNAVAILABLE`
- mixed-currency priced holdings do not aggregate into a currency-less total
- missing priced-holding currency does not aggregate into a currency-less total

## 7. Source-Label and Source-ID Behavior

Approved commentary rows with a backend `source_id` become source-bearing Home news items with:

- `source_id`: backend source ID
- `source_kind`: `ephemeral`
- `source_label`: `context_only`
- `evidence_labels`: `["context_only"]`
- `resolver`: `cockpit_chat_attached_sources`
- `resolvable`: `true`

Rows without `source_id` are marked `DATA_MISSING`, `missing_required_evidence`, `resolvable: false`, and `resolver: none`.

No source label is upgraded to `claim_verified`, `financial_truth`, or any source-backed trust label.

## 8. Chat Handoff Behavior

No legacy chat behavior was changed. The route emits source identities in the existing contract shape so the existing Home contract helper can build ChatScreen handoffs for resolvable source-bearing items. DATA_MISSING and unresolvable items remain blocked by the existing contract helper.

## 9. Tests Run and Exact Results

Preflight:

- `git branch --show-current`: `safe/cockpit-home-bff-route-v1`
- `git rev-parse --short=12 HEAD`: `c5ef4f853596`
- `git status --short --untracked-files=all`: task card only before implementation
- `git worktree list`: confirmed isolated worktree present
- task-card validate: passed
- shared registry list-active: no active jobs on retry
- isolated-root shared-registry overlap check: passed
- registry claim: passed

Validation:

- `pnpm install --frozen-lockfile`: passed; installed isolated frontend dependencies from `pnpm-lock.yaml`
- first `npx vitest ...`: failed before install because isolated worktree lacked `node_modules`; not an implementation failure
- `pnpm exec vitest run lib/cockpit-home-api.test.ts lib/cockpit-home-contract.test.ts`: passed, `2 passed`, `7 passed`
- `npx tsc --noEmit --pretty false`: passed
- `pnpm exec eslint app/api/cockpit/home/route.ts lib/cockpit-home-api.ts lib/cockpit-home-api.test.ts`: passed
- `git diff --check`: passed after removing copied task-card trailing whitespace
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_home_bff_route_v1.md`: passed with `"ok": true`

Code-reviewer skill pass:

- Critical findings: none
- Warnings fixed before final validation:
  - null numeric coercion counted missing `market_value` as zero
  - source rows without `source_id` could appear ready
  - priced holdings without currency could be aggregated into a currency-less total

## 10. Collision Risk

- Expected collision risk: MEDIUM
- Actual collision risk after retry: MEDIUM, no active registry overlap
- Contested surfaces touched: none
- Backend runtime code touched: none

## 11. DATA_MISSING

- DATA_MISSING: there is no dedicated backend Home endpoint for market session, market movers, attention queue, or Home narrative sections.
- DATA_MISSING: portfolio day-change is not available from the current holdings endpoint.
- DATA_MISSING: no live backend call was made during validation; behavior was tested with mocked HTTP surfaces only.

## 12. Whether Home UI Live Wiring Can Be Considered Next

Yes, but only as a separate task. The next task can wire Home UI to `GET /api/cockpit/home` if it preserves the visible `DATA_MISSING` states and designs how placeholder/unavailable sections should render. It should not remove the mock Home state until the UI can represent `PARTIAL` and `DATA_MISSING` cleanly.

## 13. Project Memory Save Recommendation

Recommended memory note: Cockpit Home BFF Route v1 now exists on `safe/cockpit-home-bff-route-v1` as a frontend-only Next.js route. It composes `/api/health`, `/api/cockpit/holdings`, and `/api/commentary/recent`, returns contract-shaped `PARTIAL`/`DATA_MISSING` state, preserves source-ID handoff semantics, and does not wire the Home UI yet.
