# Summary

## What Changed

`memory_signal_router.py` now resolves company write targets per statement instead of blindly fanning every accepted statement out to the memo-level ticker list.

The bounded rule is:

- zero tickers: no company-memory write unless a structured statement-level target exists
- one memo ticker: preserve existing single-company behavior
- multiple memo tickers: emit a company-memory signal only when exactly one statement-level target is explicit
- ambiguous multi-company, recap, educational, market-wide, or macro statements: do not emit company-memory writes
- supported macro/sector statements can still route through existing market-memory signal generation

The router also avoids stringifying raw dict payloads into statements by reading known text fields from dict statement items and skipping dicts with no text field.

## Root Cause Addressed

The confirmed write cause was the memo-level ticker loop in `financial-engine_v2/backend/app/services/memory_signal_router.py`, where every statement inherited every memo ticker as a company-memory target. This change replaces that loop with a deterministic statement-target resolver before `route_signals()` writes to `CompanyMemoryStore`.

## What Remains Unfixed

- Historical contaminated company-memory rows remain in place.
- Alias fragmentation remains unresolved.
- Upstream memo extractors still do not emit a full structured statement schema.
- News memo dispatch still does not pass primary-vs-mentioned company attribution into memo extraction.
- Retrieval still searches exact primary ticker scope and can surface existing contaminated rows until cleanup is separately designed.

## Cleanup Status

Historical cleanup remains blocked because it would require live memory row review, alias/canonical identity decisions, provenance classification, and operator-approved mutation policy. None of that was in scope for this safe extension.

