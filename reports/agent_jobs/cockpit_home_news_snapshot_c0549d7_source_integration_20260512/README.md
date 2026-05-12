# Cockpit Home News Snapshot c0549d7 Source Integration

Lane:
Reporting

Branch:
`codex/cockpit-home-news-snapshot-c0549d7-source-integration-20260512`

Worktree:
`/mnt/hdd-data/home/l4nd0/tenn-cockpit-home-news-snapshot-c0549d7-source-integration`

Execution mode:
SAFE EXTENSION

Contested surfaces touched:
None.

Collision risk:
LOW. The shared registry claim succeeded in a clean linked worktree, and edits are restricted to the task card plus the three allowed Cockpit Home files.

Decision:
proceed

## Summary

Integrated the source behavior from `c0549d754cb501254873b34c66d9aec7d12b95d8` without applying its old task/report artifacts.

Cockpit Home now derives partial Market Movers cards from existing `attention_queue` items whose `source_type` is `market_update_followup`. These items remain explicitly partial, unresolved `operational_trace` signals with null price/change/change-percent fields and `MARKET_MOVER_PRICE_FIELDS_MISSING` evidence. When no such follow-up exists, the existing `NO_MARKET_MOVERS_ENDPOINT` DATA_MISSING behavior remains.

The Home UI now renders partial market update signals in a separate `Market Update Signals` panel instead of passing null numeric movers through the numeric `MarketPulseCard`.

## Contract Safety

- Target layer: Client / Reporting.
- Backend authority is preserved; no backend, retrieval, ingestion, storage, memory, Qdrant, Postgres, SQLite, or financial-truth data was touched.
- Source/evidence label safety is preserved: partial movers use `operational_trace`, `resolvable: false`, `source_id: null`, and never claim `claim_verified`, `financial_truth`, or source-backed numeric evidence.
- Existing DATA_MISSING behavior remains for absent market-mover signals and upstream failures.
- No runtime process was restarted.

## Files Changed

- `docs/agent_tasks/cockpit_home_news_snapshot_c0549d7_source_integration_20260512.md`
- `cockpit-ui/lib/cockpit-home-api.ts`
- `cockpit-ui/lib/cockpit-home-api.test.ts`
- `cockpit-ui/components/cockpit/home/home-page.tsx`
- `reports/agent_jobs/cockpit_home_news_snapshot_c0549d7_source_integration_20260512/README.md`
- `reports/agent_jobs/cockpit_home_news_snapshot_c0549d7_source_integration_20260512/diff-check.json`

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_home_news_snapshot_c0549d7_source_integration_20260512.md`: PASS
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_home_news_snapshot_c0549d7_source_integration_20260512.md`: PASS
- `pnpm --dir cockpit-ui install --frozen-lockfile`: PASS; installed missing linked-worktree `node_modules`, lockfile already up to date
- `pnpm --dir cockpit-ui test cockpit-home-api.test.ts cockpit-home-contract.test.ts`: PASS, 2 files / 16 tests
- `pnpm --dir cockpit-ui exec tsc --noEmit`: PASS
- `pnpm --dir cockpit-ui exec eslint lib/cockpit-home-api.ts lib/cockpit-home-api.test.ts components/cockpit/home/home-page.tsx`: PASS
- `git diff --check`: PASS
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_home_news_snapshot_c0549d7_source_integration_20260512.md`: PASS

## DATA_MISSING

- Browser/runtime validation was not run because the task card forbids runtime restarts. Current live UI, if any, may still serve a pre-integration build.
- This integration was completed in a linked worktree. It has not been merged back into `preserve/dirty-work-20260430T065748Z`.

## Final Status

Implementation is complete in the integration worktree. The registry claim was released successfully.
