# Safe Fix Options

No fix is implemented in this audit except the isolated xfail test.

## Smallest Safe Code Boundary

Smallest later fix boundary: `financial-engine_v2/backend/app/services/memory_signal_router.py`, plus tests.

Why: the confirmed bad behavior occurs where memo-level tickers become company write targets. Fixing there can prevent recurrence without touching live data, retrieval ranking, answer synthesis, or cleanup.

## Option A: Router Gate on Statement Target

Add a pre-write target resolver inside `memory_signal_router.py`:

- infer statement target tickers from explicit ticker/company mentions in the statement
- if exactly one target is found, write only that company signal
- if no company target and statement is macro/sector, write only market memory
- if no target and not market-scoped, do not write company memory
- if multiple targets, either split only when the statement explicitly compares them, or treat as market/sector context

Pros: narrowest code change.  
Cons: still heuristic unless memo extractor emits structured targets.

## Option B: Structured Memo Signals

Change memo schema from free-form string lists to structured statement objects:

```json
{
  "statement": "...",
  "scope": "company|sector|macro|market_recap|transcript_summary",
  "target_tickers": ["A2M"],
  "mentioned_tickers": ["ATLASSIAN", "PETTIMED"],
  "evidence_span": "...",
  "source_title": "...",
  "published_at": "..."
}
```

Pros: correct contract and provenance.  
Cons: touches extractors and tests in addition to router.

## Option C: Conservative Block Multi-Ticker Company Writes

When a memo has more than one ticker, do not create company-memory writes unless the statement explicitly contains exactly one target ticker or canonical company name. Route macro/sector content to market memory only.

Pros: lowest contamination risk.  
Cons: may drop some useful company memory until structured extraction exists.

## Recommended Later Path

Implement Option C first in `memory_signal_router.py` with focused tests, then follow with Option B for richer provenance.

Do not fix this in retrieval. Retrieval-side filtering would hide symptoms while leaving contaminated durable memory in place.

