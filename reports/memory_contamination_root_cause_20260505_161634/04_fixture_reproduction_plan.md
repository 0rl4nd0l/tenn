# Fixture Reproduction Plan

## Added Fixture

Added one strict xfail test:

```text
financial-engine_v2/backend/tests/test_memory_signal_router.py::test_multi_topic_commentary_does_not_fanout_primary_company_signal
```

Validation:

```bash
financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_memory_signal_router.py -q
```

Result:

```text
7 passed, 1 xfailed in 0.89s
```

## Fixture Shape

Input memo:

- source_type: youtube_transcript
- primary subject implied by content: A2M recall
- tickers list: A2M, ATLASSIAN, PETTIMED, CHRYSOS, ACC
- company statements: A2M recall, Atlassian result/share-price item, Pettimed capital raising, Chrysos trading update/share-price item, Accent downgrade/share-price item
- macro statement: inflation and interest rates

Expected future behavior encoded by the xfail:

- A2M memory can contain the A2M recall
- non-A2M company memories must not contain the A2M recall
- macro/rates content must appear in market memory
- company memories must not contain the macro/rates statement

Current behavior:

- The test xfails because the router writes the A2M recall to every ticker in the memo list.

## Temp-DB Manual Reproduction

The same fixture was executed against temp-directory `CompanyMemoryStore` and `MarketMemoryStore`. It produced 35 company writes and 1 market write:

```text
A2M entries 7 unrelated 6
ATLASSIAN entries 7 unrelated 6
PETTIMED entries 7 unrelated 6
CHRYSOS entries 7 unrelated 6
ACC entries 7 unrelated 6
```

This did not touch live DBs.

## Next Fixture Improvements

Add a non-xfail passing regression only after the router is fixed. It should assert:

- per-statement target tickers are honored
- source/source_id/published_at/evidence span metadata survives routing
- a macro-only statement creates no company-memory write
- a transcript-level summary creates no company-memory write unless scoped to a target company

