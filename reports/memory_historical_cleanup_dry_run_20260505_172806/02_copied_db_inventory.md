# Copied DB Inventory

## Live Paths Identified

- Company memory live candidate: `financial-engine_v2/data/reports/research_memory/company_memory.sqlite`
- Market memory live candidate: `financial-engine_v2/data/reports/research_memory/market_memory.sqlite`
- User thesis memory live candidate: `financial-engine_v2/data/reports/research_memory/user_thesis_memory.sqlite`
- Empty fallback company DB: `financial-engine_v2/reports/research_memory/company_memory.sqlite` had zero memory rows and was not used.

## Copied Paths

- Company memory copy: `/mnt/sdb2/home/l4nd0/tenn/reports/memory_historical_cleanup_dry_run_20260505_172806/copied_db/company_memory.sqlite`
- Market memory copy: `reports/memory_historical_cleanup_dry_run_20260505_172806/copied_db/market_memory.sqlite`
- User thesis copy: `reports/memory_historical_cleanup_dry_run_20260505_172806/copied_db/user_thesis_memory.sqlite`

## Company Schema

The copied company DB contains `company_memory`, `memory_entries`, and `change_log`. `memory_entries.entry_id` is the stable row id and spans 1..1998 with 1998 distinct ids. Supported status semantics in code are `active` and `expired`; no `quarantined` status exists.

## Pre-Dry-Run Counts

- Total rows: 1,998
- Active rows: 1997
- Expired rows: 1
- Company scopes: 83
- Change-log rows before dry-run: 2,471
- Existing audit table: yes, `change_log`

## Checksums

- Copied company DB before dry-run: `aa25e14894be56d601ce4ec9b4fd48e67eaf94b6cf60db13eae52c00c90ba5b1`
- Copied company DB after dry-run: `1358344ca9001ea6ac03d708a2298b5939b6052d8d59bc5075e785eeffd96d2a`
- Live company DB after dry-run: `aa25e14894be56d601ce4ec9b4fd48e67eaf94b6cf60db13eae52c00c90ba5b1`
