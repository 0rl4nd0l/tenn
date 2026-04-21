# Daily Market Update Standard

## Scope and Trigger

Apply this standard for end-of-day or daily market wrap requests that summarize broad market movement, major movers, and key drivers.

## Inputs and Evidence Contract

1. Treat backend-provided market and ticker data as authoritative.
2. Distinguish confirmed market facts from interpretation.
3. Timestamp time-sensitive claims when timing context exists.
4. Do not infer absent price, volume, or macro values.
5. If coverage is partial (missing sectors/tickers), disclose that explicitly.

## Execution Steps

1. Market Overview Pass:
Summarize broad direction and notable breadth in plain terms.

2. Major Movers Pass:
Highlight the most significant movers with concise evidence-backed rationale.

3. Driver Pass:
Explain plausible drivers with clear confidence labeling.

4. Watchlist Impact Pass:
If watchlist context exists, include implications for monitored names.

5. Unknowns Pass:
List missing or stale evidence that limits confidence.

## Output Contract

Use this top-level section order:

1. `Market Summary:`
2. `Major Movers:`
3. `Drivers and Context:`
4. `Watchlist Impact:`
5. `Unknowns:`

Every substantive factual line must include user-visible source grounding.

## Memory and Follow-up Rules

1. Do not write memory automatically from daily update output.
2. Follow-up actions (for example ingest/backfill) must be explicit recommendations.
3. Any proposed watchlist action should be confirmation-gated.
