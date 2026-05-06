# Gap Mapping

G008 - non-news no-hit tools:

- `get_financials` empty canonical rows now emit
  `missing_required_evidence`, `no_hit`, and `operational_trace`.
- `search_announcements`, local context/company dump, dossier recall, web
  search/fetch no usable rows, watchlist alert misses, screener misses, and TV
  indicator misses now emit no-hit source metadata or answer metadata.
- No-hit items do not set `claim_verified`.
- Operational traces remain `operational_trace` and are not labelled
  `financial_truth`.
- Pure no-hit/runtime trace sources do not satisfy the source contract for
  polished financial claims.

G009 - web/deep/runtime degradation:

- `search_web` and `fetch_url` failures now emit `degraded_runtime` and
  `operational_trace`.
- Deep research failures, including failed synthesis with a partial research
  payload, now emit `degraded_runtime`.
- Tool executor exceptions and ok=false failures carry evidence labels and
  `source_coverage_status`.
- Agent loop merges tool-result evidence state into final routing metadata.
- Explicit web-search shortcut exceptions now return degraded evidence and
  routing metadata instead of empty evidence.
- Partial evidence plus runtime failure keeps useful evidence and adds the
  degraded state.
