# Change Summary

## Production Change

File: `financial-engine_v2/backend/app/services/memory_signal_router.py`

Changes:

- Added statement-level target resolution for company-memory signals.
- Preserved existing single-ticker memo behavior.
- Changed multi-ticker memo behavior so company-memory writes require exactly one explicit target.
- Kept existing market-memory generation for macro/sector statements.
- Added dict statement parsing for known statement text fields.
- Skips dict payloads without text fields instead of writing `str(dict)` into company memory.

## Test Change

File: `financial-engine_v2/backend/tests/test_memory_signal_router.py`

Changes:

- Converted `test_multi_topic_commentary_does_not_fanout_primary_company_signal` from strict xfail to passing.
- Expanded the mixed A2M/Atlassian/Pettimed/Chrysos/Accent fixture with unrelated memo tickers BHP and COH to prove no broad fanout.
- Added a single-company preservation regression.
- Added an ambiguous multi-ticker no-target regression.
- Added a structured statement-level target regression.
- Added a raw-dict no-stringification regression.

## Behavior Deferred

- No historical cleanup.
- No alias canonicalization.
- No structured memo schema migration.
- No retrieval/ranking change.
- No company analysis behavior change.
- No source-label change.

