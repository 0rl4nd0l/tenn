# Alias Fragmentation Root Cause

## Classification

Root cause: CONFIRMED before-write fragmentation, preserved during write, amplified during retrieval.

## Evidence

The stocktake alias matrix shows split memory scopes such as:

- A2M / A2 MILK
- ACC / ACCENT GROUP
- PET / PETT / PETTIMED
- GCM / GCMC / GCM CORPORATION
- MAR / MARINO / MARINO AND CO
- KEY / KEYP / KEY PETROLEUM
- END / EDV / ENDV / ENDEAVOR GROUP

The matrix reports retrieval as "only primary_ticker exact company_id" for these groups. Evidence: `reports/full_system_stocktake_20260505_152038/04A_memory_alias_fragmentation_matrix.csv`.

## Code Path

1. Memo extractors normalize ticker strings by uppercasing list items, but they do not canonicalize to ASX identifiers. Evidence:
   - `commentary_memo_extractor.py:177-179`
   - `news_memo_extractor.py:165-167`

2. The router copies each ticker string into `entity_id`. Evidence: `memory_signal_router.py:251-264`.

3. `CompanyMemoryStore.update_company_memory(company_id, signal)` uppercases the incoming company_id and stores it as-is. Evidence: `company_memory.py:193-199`, `:253-278`.

4. Retrieval does not search alias groups. It retrieves only active rows for `entities["primary_ticker"]`. Evidence: `company_memory.py:439-460`.

## Timing

Before write: alias fragmentation is introduced by LLM memo output, entity-linker output, or manually supplied memory IDs.

During write: the company store preserves the exact normalized string as `company_id`.

During retrieval: exact primary-ticker lookup makes aliases invisible unless the query resolves to the same stored string. This explains stale or missing answers, but it does not create the initial fanout.

## Constraint

Alias cleanup is HIGH risk. Do not canonicalize rows in live storage until there is an authoritative ASX identity audit, a reversible archive/expire plan, and a source-preserving mapping of old IDs to canonical IDs.

