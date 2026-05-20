# Memory Contamination Live Inventory Read-only

Generated: 2026-05-19T13:57:04Z

## Executive Verdict

- `LIVE_ACTIVE_CONTAMINATION_PRESENT`
- `CLEANUP_READY_FOR_OPERATOR_REVIEW`
- `ACTIVE_MEMORY_PATH_NVME`

## Confirmed Facts

- Active DB path: `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/reports/research_memory/company_memory.sqlite`.
- Container path: `/data/reports/research_memory/company_memory.sqlite`.
- Storage location: NVMe2 (`/mnt/tenn-nvme2`, mounted from `/dev/nvme0n1p1`).
- Read-only SQLite open mode: `mode=ro&immutable=1` with `PRAGMA query_only=ON`.
- Tables present: `company_memory`, `memory_entries`, `change_log`.
- `memory_entries` rows: total `2440`, active `147`, expired/closed `2293`.
- Distinct company IDs: `184`; distinct source IDs: `132`.
- Active duplicate statement/source clusters: `0` clusters, `0` active rows.
- Active source-fanout clusters at threshold `active rows >= 5` and `distinct company_id >= 3`: `1` top-50 cluster, source `news:art_c0195feddb42ee1a1f11268d`, `5` active rows across `4` company IDs.
- Known historical source checks: youtube_transcript:asx-daily-rundown-atlassian-lifts-tech-a2-milk-recall-shock-accent-group-all-time-lows: active=6 total=1555; news:art_e4faef3c4644fe5bb3b66e32: active=4 total=160.
- Known statement checks: PETTIMED: active=0 total=176; A2 MILK: active=7 total=328; ACCENT GROUP: active=0 total=190; capital raising at 1 cent: active=0 total=67; share price dropped: active=3 total=104. Across all known source/statement checks this is `14` deduped active entry IDs.
- Ticker spot checks: A2M active=7 dup=0, A2 MILK active=0 dup=0, BHP active=4 dup=0, COH active=0 dup=0, ASX active=0 dup=0, PET active=0 dup=0, PETT active=0 dup=0, PETTIMED active=0 dup=0.
- Prior approved manifest comparison: active `0`, expired/closed `963`, missing `0`.
- Prior manual-review manifest comparison: active `3` (`283`, `310`, `1129`), expired/closed `247`, missing `0`.

## Path Resolution

Live containers resolve `app.services.source_registry.RESEARCH_MEMORY_ROOT` to `/data/reports/research_memory`. Docker maps `/data` to `/mnt/tenn-nvme2/tenn/financial-engine_v2/data`, so the active host file is the NVMe2 candidate.

The container env still contains `TENN_RESEARCH_MEMORY_ROOT=/mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/data/reports/research_memory`, but that absolute host path does not exist inside `fe_backend` or `fe_worker`; code falls through to `/data/reports/research_memory`. The HDD candidate has the same SHA-256 as the NVMe2 active file, but it is not the active container path.

## Inferred Facts

- Prior approved cleanup likely succeeded historically for the approved manifest: the approved manifest comparison reports zero active approved candidates in the current active DB.
- No exact cross-company duplicate normalized-statement/source clusters remain active.
- Remaining active review surface is narrower: one source-fanout threshold cluster, `14` deduped active entries tied to known historical source/statement checks, and `3` still-active manual-review manifest rows. These are not approved cleanup candidates and require operator review rather than automatic cleanup.
- Current surfacing risk remains possible for any active ticker-matching rows because read paths select active `memory_entries`; exact route surfacing was classified from code/read inventory only, with no live API calls.

## Reader Surfacing Risk

- Ticker-specific company analysis: current risk for ticker-matching active rows. `CompanyMemoryStore.retrieve()` calls `list_entries(company_id, status="active")` and ranks entries before returning them to orchestrated evidence (`financial-engine_v2/backend/app/services/company_memory.py:448`).
- Chat memory context: current risk when a query plan includes `company_memory`. `QueryOrchestrator` instantiates `CompanyMemoryStore`, then `MemoryAssembler.assemble()` calls each planned provider and emits a memory read event (`financial-engine_v2/backend/app/services/query_orchestrator.py:1581`, `financial-engine_v2/backend/app/services/memory_assembler.py:61`).
- `/api/context/company_dump`: current risk for scoped ticker dumps. The route calls `_load_company_memory()` with default `entry_status="active"` and includes the result in the response (`financial-engine_v2/backend/app/api/context.py:318`, `financial-engine_v2/backend/app/api/context.py:1601`).
- Memory Workbench: current risk for scoped loads. The UI fetches `/api/cockpit/memory?...` and `/api/cockpit/memory/company-dump?...`, and the BFF proxies company dump to `/api/context/company_dump` (`cockpit-ui/components/cockpit/memory/memory-screen.tsx:936`, `cockpit-ui/app/api/cockpit/memory/company-dump/route.ts:11`).
- Source drawer/evidence envelope: current risk for memory-context evidence labeling. Cockpit source labeling adds `memory_context` for memory source IDs and appends company-memory payload sources when evidence type is `company_memory` (`financial-engine_v2/backend/app/routes/cockpit_api.py:1515`, `financial-engine_v2/backend/app/routes/cockpit_api.py:2185`).

## DATA_MISSING

- Writer job IDs for remaining active duplicate/fanout rows were not reconstructed.
- Full source spans and original memo extraction context were not reconstructed.
- `/tmp/batch5_selected_targets_export.csv` and `/tmp/batch6_selected_targets_for_run.csv` were not present; the durable historical manifest CSVs were used instead.
- No live chat, `/api/context/company_dump`, Memory Workbench, or Cockpit routes were called because those paths may write read/session/flag artifacts.

## SQL / Query Methodology

Active rows used:

```sql
WHERE lower(status) = 'active'
```

Duplicate statement clusters used:

```sql
SELECT normalized_statement, source_id, COUNT(*), COUNT(DISTINCT company_id)
FROM memory_entries
WHERE lower(status) = 'active'
GROUP BY normalized_statement, source_id
HAVING COUNT(*) > 1 AND COUNT(DISTINCT company_id) > 1;
```

Source-fanout clusters used:

```sql
SELECT source, source_id, COUNT(*), COUNT(DISTINCT company_id)
FROM memory_entries
WHERE lower(status) = 'active'
GROUP BY source, source_id
HAVING COUNT(*) >= 5 AND COUNT(DISTINCT company_id) >= 3
ORDER BY COUNT(DISTINCT company_id) DESC, COUNT(*) DESC
LIMIT 50;
```

Known historical checks used `LIKE` searches over `source_id` and short statement substrings, reporting counts plus capped row IDs and previews only.

Ticker spot checks used case-insensitive exact `company_id` matches for: `A2M, A2 MILK, BHP, COH, ASX, PET, PETT, PETTIMED`.

## Cleanup Readiness

CLEANUP_READY_FOR_OPERATOR_REVIEW.

If cleanup proceeds later, it needs a separate operator-approved task with a dry-run review manifest, explicit row IDs, manual-review exclusions, backup/checksum, and a bounded status-only mutation plan. This audit does not authorize expiry, delete, rewrite, alias canonicalization, Qdrant/news resync, or LLM cleanup.

## Do Not Do

- No delete.
- No expiry.
- No rewrite.
- No alias canonicalization.
- No Qdrant/news resync.
- No LLM cleanup authority.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/memory_contamination_live_inventory_readonly_v1_20260519.md` -> `ok: true`.
- Read-only DB open mode: `mode=ro&immutable=1`; `PRAGMA query_only=ON`.
- JSON artifact validation with `jq empty` -> `JSON_OK`.
- CSV artifact validation -> `active_duplicate_clusters.csv` rows `0`; `active_source_fanout_clusters.csv` rows `1`.
- `git diff --check` -> passed.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/memory_contamination_live_inventory_readonly_v1_20260519.md` -> `ok: true`.
- Final `git status --short` and registry release were run after this README update.
