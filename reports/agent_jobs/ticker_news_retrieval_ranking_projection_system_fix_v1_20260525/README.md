# Ticker News Retrieval Ranking Projection System Fix

## Summary

- Branch: `safe/ticker-news-retrieval-ranking-projection-system-fix-v1-20260525`
- Base HEAD: `173a8750caa4602e5791ee072673db17e708c5d3`
- Final HEAD ref: `safe/ticker-news-retrieval-ranking-projection-system-fix-v1-20260525@HEAD`
- Worktree: `/home/l4nd0/tenn-ticker-news-retrieval-ranking-projection-system-fix-v1-20260525`
- Task card: `docs/agent_tasks/ticker_news_retrieval_ranking_projection_system_fix_v1_20260525.md`
- Registry: active claim for this job, no overlap conflicts.

## Ticker Basket

Selected from local Qdrant evidence, not assumptions:

- `A2M`: canary, 24 linked / 16 primary Qdrant news points.
- `BHP`: large/common ticker, 2155 linked / 790 primary.
- `CSL`: company-name-heavy healthcare ticker, 2184 linked / 99 primary.
- `XRO`: ambiguity/company-name ticker, 2452 linked / 14 primary.
- `NST`: previously failed-style resources ticker, 2120 linked / 18 primary.
- `MIN`: broad resources ticker with primary evidence, 3621 linked / 159 primary.
- `COH`: no current Qdrant news evidence in this corpus.
- `WOW`: low/no-local-news control in this corpus.

## Confirmed Facts

- Live `/api/cockpit/news/status` reports Qdrant route ok and canonical SQLite projection missing.
- Current canonical `reports/qual_context/news.sqlite` and `news_articles.sqlite` are absent.
- Legacy `/mnt/sdb2/.../reports/qual_context/news.sqlite` exists but is not the current consumer.
- Pre-fix live backend retrieved local news for A2M/BHP/CSL/XRO/NST/MIN but returned `claim_verified_source_count: 0`.
- Pre-fix live backend projected local news as `local_news_context` plus `context_only`.
- COH and WOW remain honest no-hit / `DATA_MISSING` controls.

## Inferred Facts

- The running backend is mounted from the canonical worktree, not this isolated branch, so live post-fix chat smoke would require backend restart.
- Because restart was not approved in this task, post-fix proof is code-level against live Qdrant plus unit/route test validation.

## DATA_MISSING

- Canonical SQLite news projection is missing.
- COH and WOW have no local Qdrant news evidence in the current corpus.
- Live post-fix endpoint smoke is missing because the running backend does not serve this branch and no restart was performed.

## Root Cause

Qdrant-backed local news existed across the representative ticker universe, but:

- ticker-filter parity omitted `primary_ticker`;
- ticker-scoped candidate breadth was too narrow for broad ASX news baskets;
- ranking favored broad linked market wraps and scan-list items over primary ticker articles;
- source-pack assembly marked successful news hits as context-only, so the newly landed guard correctly returned `DATA_MISSING`.

## Fix Implemented

- `rag.py`
  - Added `primary_ticker` to news ticker filter parity.
  - Widened ticker-scoped Qdrant candidate retrieval.
  - Added generic ranking signals: primary/stored ticker match, title ticker mention, broad-roundup penalty, linked-ticker breadth penalty, and candidate-relative recency.

- `cockpit_api.py`
  - Successful direct `news_search` and successful agent `search_news` hits now project as `claim_verified` + `local_news_context`.
  - Explicit `context_only`, no-hit, data-insufficient, missing-required, and degraded rows remain unverified.
  - `chat_evidence_guard.py` was intentionally not changed.

## Validation

- `python3 -m py_compile financial-engine_v2/backend/app/services/rag.py financial-engine_v2/backend/app/routes/cockpit_api.py`: PASS.
- Ruff changed backend files/tests: PASS.
- `tests/test_rag_news_query.py tests/test_build_ui_sources.py`: 65 passed.
- `tests/test_chat_evidence_guard.py tests/test_cockpit_news_status.py tests/test_sources.py tests/test_cockpit_api_models.py tests/test_route_parity_contract.py`: 47 passed, existing warnings.
- `tests/test_cockpit_api_chat_stream.py`: 62 passed.
- `git diff --check`: PASS.
- Task-card validate/check-overlap/check-diff: PASS.

## Live Smoke

Not run post-fix. The running backend serves the canonical checkout, not this isolated worktree. Per task instruction, I stopped rather than restarting backend services.

## Forbidden Mutation Attestation

No DB mutation, Qdrant mutation, news-store mutation, reindex, resync, backfill, projection rebuild/repair, migration, parser routing change, canonical financial truth write, Tenn memory write, runtime/model/GPU config edit, UI change, destructive git operation, or one-off ticker alias hardcoding occurred.

## What This Proves

- Locally available Qdrant ASX news is discoverable for multiple non-A2M tickers.
- Ranking now materially improves primary ticker and recent local-news placement for the representative basket.
- Successful local-news hits are handed to chat metadata as claim-verified local news.
- The source-grounding guard remains intact and still blocks context-only/no-hit/degraded cases.

## What This Does Not Prove

- It does not prove a live deployed endpoint result after restart.
- It does not repair or rebuild canonical SQLite news projection.
- It does not create news for missing-control tickers.
- It does not fully solve every relevance case; NST still shows a broad linked resources item above older primary NST evidence.

## Final Git Status

Expected changed files are limited to the task card, two backend implementation files, two backend tests, and this report bundle. Integration commit exists on the isolated branch; merge/restart remains pending operator workflow.

## Project Memory Save Recommendation

Save: Qdrant `news_chunks` had broad evidence while canonical SQLite projection was absent; the safe code-only fix was primary_ticker parity + wider/re-ranked ticker news candidates + claim-verified source projection for successful local news, without changing `chat_evidence_guard.py`.
