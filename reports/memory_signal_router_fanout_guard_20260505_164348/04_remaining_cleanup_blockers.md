# Remaining Cleanup Blockers

Historical company-memory cleanup remains blocked.

## Why It Is Blocked

Cleanup would require decisions and evidence that are outside this task:

- a reviewed list of contaminated rows to expire
- a canonical identity/alias policy for rows such as `PET`, `PETT`, `PETTIMED`, `A2M`, and `A2 MILK`
- a rule for distinguishing primary company, mentioned company, sector, macro, recap, and educational statements
- an operator-approved mutation plan for live qualitative memory
- rollback/reporting artifacts for every expired or rewritten row

## Explicitly Not Done

- no live memory rows cleaned
- no live memory rows expired
- no live memory rows rewritten
- no DB migration
- no alias normalization in storage
- no ingestion or reprocessing
- no Qdrant reindex
- no retrieval or ranking tuning

## Current Risk After This Fix

New memo-level fanout from this router path is guarded. Existing contaminated rows can still be retrieved until a separate cleanup lane safely identifies and expires them.

