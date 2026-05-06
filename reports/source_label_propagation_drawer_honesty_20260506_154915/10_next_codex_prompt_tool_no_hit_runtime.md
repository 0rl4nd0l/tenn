# Next Codex Prompt: Tool No-Hit + Runtime Metadata

Lane: Query Orchestration
Supporting lane: Provenance
Execution mode: SAFE EXTENSION MODE after preflight

## Mission

Close the remaining no-hit/degraded-runtime consistency gaps without changing retrieval ranking, ingestion, Qdrant, memory, or financial truth.

## Target Gaps

- G008: non-news operational no-hit tools should emit `no_hit` or `missing_required_evidence`, not generic context.
- G009: web/deep-research tool failures should surface `degraded_runtime` when the answer depends on those failed paths.

## Required Guardrails

- Do not reindex Qdrant.
- Do not mutate `news.sqlite`.
- Do not broaden synthesis prompts.
- Do not redesign source labels.
- Do not expose raw chain-of-thought.
- Do not touch holdings/watchlist/marketplace fixes except where a no-hit source label is directly emitted.

## Suggested Tests

- zero-result `tv_screener`/`screen_tickers` paths are not claim verified
- web/deep-research failure metadata includes `degraded_runtime`
- no-hit answers do not render as source-backed
- holdings still remain `local_personal_data`
- A2M local news still remains `local_news_context`
