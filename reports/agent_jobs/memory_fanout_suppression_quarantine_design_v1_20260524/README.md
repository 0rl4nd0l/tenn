# Memory Fanout Suppression Quarantine Design

Status: `complete_design_no_mutation`.

This child completed the audit/design phase. It did not mutate memory, Qdrant, news, Postgres, source registry, migrations, runtime config, or chat routes.

## Confirmed

- The latest read-only inventory artifact reports 147 active company-memory rows across 59 company IDs.
- It reports 0 active duplicate-statement clusters.
- It reports 4 active source-fanout suspicious clusters covering 17 entries.
- It reports all 17 suspicious entries selectable in offline dry-run scoring.
- Current read-path code can surface active suspicious rows through `CompanyMemoryStore.retrieve()`, `MemoryAssembler`, and Query Orchestrator memory selection when a query plan includes company memory.

## Recommendation

Do not delete, expire, migrate, or silently hide these rows from production in this goal.

Use the report-local `candidate_quarantine.json` as an operator review seed. The next safe implementation is an exact-entry read-path quarantine guard only after operator approval, with visible filtered/quarantined counts and tests proving memory remains context-only.

## DATA_MISSING

- Full source article/transcript text and source spans for every candidate row.
- Operator decisions for preserve/suppress/expire.
- Backup/checksum proof for any future mutation.
- Live route proof, intentionally skipped because memory read routes may emit operational artifacts.

## Artifacts

- `fanout_suppression_design.md`
- `candidate_quarantine.json`
- `candidate_quarantine.csv`
- `status.json`
- `validation.json`
