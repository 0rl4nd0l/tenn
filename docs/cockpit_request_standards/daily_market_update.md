# Daily Market Update Standard

## Scope and Trigger

Apply this standard for:
- intraday market preview or midday update requests
- end-of-day market wrap requests
- broad daily market movement summaries
- daily market reports intended to support watchlist review or later research follow-up

The report mode must be identified explicitly:
- `Midday Update`
- `End-of-Day Wrap`
- `Partial Session Update`

## Inputs and Evidence Contract

1. Treat backend-provided market, ticker, announcement, and news data as authoritative within their covered scope.
2. Separate clearly:
   - confirmed market facts
   - confirmed event evidence
   - inferred interpretation
   - unresolved unknowns
3. Timestamp time-sensitive claims when timing context exists.
4. Do not infer absent price, volume, breadth, macro, sector, or index values.
5. Do not claim a driver as causal unless evidence supports it with reasonable confidence.
6. If coverage is partial, stale, uneven, or otherwise incomplete, disclose that before the main summary.
7. If the available evidence bundle is materially insufficient and more retrieval is possible, attempt additional gathering before producing the final update.
8. Do not treat missing data as negative evidence.

## Web and External Retrieval Rules

1. Prefer backend-provided market, ticker, announcement, and news data as the primary source of truth within covered scope.
2. If coverage is materially incomplete and additional retrieval is possible, Tenn may use web search or other approved retrieval tools to strengthen the update.
3. Web search or external retrieval may be used to:
   - fill coverage gaps
   - strengthen context
   - confirm notable drivers
   - improve breadth across movers, sectors, and relevant events
4. Web-sourced context must be clearly distinguished from backend-confirmed facts.
5. Do not use web search to fabricate absent numeric market data; if values remain unavailable, disclose them as missing.
6. If backend and external evidence conflict, state the conflict explicitly rather than silently choosing one.

## Coverage Sufficiency Gate

Before synthesis, check whether the update has enough evidence for:
- broad market or index direction
- market breadth or participation
- major movers
- key announcements and news drivers
- watchlist coverage, if applicable

If any of the above is materially incomplete:
- disclose the gap
- attempt deeper retrieval if possible
- then continue with a partial-confidence output or abstain from unsupported claims

## Execution Steps

1. **Market Overview Pass**
- Summarize broad direction, participation, and whether moves were broad-based or concentrated.
- Include major sector leadership and laggards where available.

2. **Major Movers Pass**
- Separate:
  - top winners
  - top losers
  - event-driven movers
  - watchlist movers, if applicable

3. **Drivers and Context Pass**
- For each major theme or mover, label the driver as one of:
  - `Confirmed driver`
  - `Likely driver`
  - `Possible driver`
  - `Unknown driver`

4. **Watchlist Impact Pass**
- If watchlist context exists, classify names as:
  - thesis strengthened
  - thesis weakened
  - monitor only
  - no material change

5. **Recommended Follow-ups Pass**
- Recommend explicit next actions only where justified, such as:
  - deeper company analysis
  - announcement review
  - news backfill
  - thesis refresh
  - no action

6. **Unknowns Pass**
- List missing, stale, conflicting, or weak evidence that limits confidence.

## Output Contract

Use this top-level section order:

1. `Market Summary:`
2. `Major Movers:`
3. `Drivers and Context:`
4. `Watchlist Impact:`
5. `Recommended Follow-ups:`
6. `Unknowns:`

Add a short header line before the sections stating:
- report mode
- market window or time context
- whether coverage is full or partial

Every substantive factual line must include user-visible source grounding.

## Memory and Save-Candidate Rules

1. Do not write memory automatically from daily update output.
2. If the update contains material developments relevant to watchlist, thesis, or ongoing research context, create a short `Proposed Memory Candidates:` block after the main report.
3. Proposed memory candidates must:
   - be evidence-bound
   - distinguish confirmed facts from interpretation
   - remain uncommitted until explicit user confirmation
4. Do not convert daily commentary into persistent thesis memory without explicit user approval.

## Follow-up and Action Rules

1. Follow-up actions must be explicit recommendations, not silent side effects.
2. Any proposed watchlist action must be confirmation-gated.
3. Do not auto-ingest conclusions from the daily update into company memory, market memory, or user thesis memory.
4. If a stronger conclusion depends on missing evidence, recommend the exact retrieval or analysis step needed.