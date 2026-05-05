# Fanout Root Cause

## Confirmed Cause

The direct fanout bug is in:

- `financial-engine_v2/backend/app/services/memory_signal_router.py:238-267`
- `financial-engine_v2/backend/app/services/memory_signal_router.py:208-235`

`_signals_for_statement()` receives one memo-level ticker list. If the list is non-empty, it loops through every ticker and appends a company signal with the same statement and `entity_id=ticker`. `route_signals()` writes each of those company signals to company memory.

This means fanout scale is approximately:

```text
company writes = accepted statements * memo-level ticker count
```

The only de-dupe before persistence is `_dedupe_signals()` on `(type, target, normalized_statement)`, which preserves the same statement once for each distinct target ticker. Evidence: `memory_signal_router.py:685-704`.

The company store then de-dupes only within a single company scope. Evidence: `company_memory.py:525-543`.

## Why Unrelated Company Statements Reach BHP, COH, WES, ASX

The router does not know which statement belongs to which company. A transcript that mentions A2M, Atlassian, Pettimed, Chrysos, Accent, BHP, COH, WES, ASX, or any other extracted alias creates one shared `tickers` list. Every accepted statement is written under every extracted ticker. So:

- an Atlassian statement is written under BHP/COH/WES/ASX if those appear in the memo ticker list
- an A2M recall statement is written under non-A2M tickers if those appear in the memo ticker list
- macro statements are written under every ticker before a macro market-memory signal is also created

## Stocktake Corroboration

`04A_memory_duplicate_fanout_clusters.csv` reports the largest cluster as:

- statement: `pettimed s capital raising at 1 cent per share`
- row_count: 67
- entity_count: 50
- source: `youtube_transcript:asx-daily-rundown-atlassian-lifts-tech-a2-milk-recall-shock-accent-group-all-time-lows:88e960386e503796`
- likely_cause: transcript/video extraction fanout

Parsed summary of the duplicate/fanout CSV:

- 107 clusters total
- 43 commentary/youtube clusters, 1555 total rows, max 50 entities
- 64 newspaper4k clusters, 322 total rows, max 8 entities

`04A_memory_scope_classification.csv` reports 951 sampled rows, 634 likely contaminated rows, 82 raw dict-like rows, and 905 duplicate/fanout rows.

## Synthetic Reproduction

The synthetic reproduction created a memo with:

- primary subject: A2M product recall
- mentioned companies: ATLASSIAN, PETTIMED, CHRYSOS, ACC
- macro/rates content

Read-only/temp-DB observed behavior:

```text
route_counts 35 1
A2M entries 7 unrelated 6
ATLASSIAN entries 7 unrelated 6
PETTIMED entries 7 unrelated 6
CHRYSOS entries 7 unrelated 6
ACC entries 7 unrelated 6
macro_entries_interest_rates 1
```

This confirms current behavior fails the desired contract: other companies receive the A2M recall, and A2M receives unrelated recap statements.

## Not Caused Solely by Entity Linking

Entity linking can over-broaden news articles, and LLM memo extraction can over-broaden commentary tickers. But even a perfectly extracted list of "all mentioned companies" is unsafe because the router treats mentioned tickers as write targets for every statement.

