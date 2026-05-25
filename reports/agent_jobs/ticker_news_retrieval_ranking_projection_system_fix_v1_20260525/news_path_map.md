# News Path Map

Job: `ticker_news_retrieval_ranking_projection_system_fix_v1_20260525`

## Runtime Surface

- Running backend: `fe_backend` on `127.0.0.1:8000`.
- Running backend mount: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/backend -> /app`.
- Worktree under fix: `/home/l4nd0/tenn-ticker-news-retrieval-ranking-projection-system-fix-v1-20260525`.
- Live backend therefore does not serve this branch's changed code without a backend restart. No restart was performed.

## End-to-End Path

1. `/api/cockpit/news/status`
   - Route owner: `financial-engine_v2/backend/app/routes/cockpit_api.py`.
   - Status service: `financial-engine_v2/backend/app/services/news_health_status.py`.
   - Reports Qdrant route reachability and canonical SQLite projection state.
   - Current live status reports Qdrant ok, canonical SQLite projection missing, legacy SQLite evidence not current consumer, and chat synthesis still `DATA_MISSING` on the pre-fix running backend.

2. Direct news route
   - Route: `POST /rag/query` with `source="news"`.
   - Owner: `financial-engine_v2/backend/app/main.py` delegates to `financial-engine_v2/backend/app/services/rag.py::query_news_chunks`.
   - Storage: Qdrant collection `news_chunks`.
   - Pre-fix issue: ticker filter matched `ticker` and `tickers`, but not `primary_ticker`.
   - Fix: ticker filter now includes `primary_ticker`.

3. Qdrant news retrieval
   - Embeds query through the existing embedding path, searches `news_chunks`, and normalizes results.
   - Pre-fix issue: ticker-scoped candidate limit was too narrow for broad ASX news baskets; ranking favored high semantic scores from broad market wraps.
   - Fix: ticker-scoped searches fetch a wider candidate set, then re-rank by primary/stored ticker match, title ticker mention, broad roundup penalty, linked-ticker breadth penalty, and candidate-relative recency.

4. news.sqlite path
   - Current canonical projection paths in this worktree are absent: `reports/qual_context/news.sqlite` and `reports/qual_context/news_articles.sqlite`.
   - Legacy `/mnt/sdb2/home/l4nd0/tenn/reports/qual_context/news.sqlite` exists, but status already labels it as not the current consumer.
   - No projection rebuild, repair, migration, or copy was performed.

5. Cockpit direct ticker news chat
   - `cockpit.core.chat.ChatController._try_news_shortcircuit` handles messages like `news for BHP`.
   - It calls `ToolRouter.get_news_context`, which prefers backend `/rag/query` and falls back to SQLite only if configured.
   - Evidence arrives at backend route assembly as `{"type": "news_search", "details": {"hits": [...]}}`.

6. Agent-loop news chat
   - `cockpit.core.agent_loop.AgentLoop` can prefetch or execute `search_news`.
   - Evidence arrives at backend route assembly as `{"tool": "search_news", "result": {"ok": true, "hits": [...]}}`.

7. Source pack creation and guard handoff
   - Owner: `financial-engine_v2/backend/app/routes/cockpit_api.py::_build_ui_sources`.
   - Pre-fix issue: successful local-news hits were projected as `local_news_context` plus `context_only`, so `claim_verified_source_count` remained zero and recent-news/source-grounding guards returned `DATA_MISSING`.
   - Fix: successful `news_search` hits and successful `search_news` tool hits are projected as `claim_verified` plus `local_news_context`. Explicit `context_only`, no-hit, data-insufficient, missing-required, and degraded rows remain unverified.
   - Guard file `chat_evidence_guard.py` was not changed.

## First Failing Stage By Ticker

- `A2M`: source pack misclassified retrieved local news as context-only; pre-fix ranking also favored a linked broad item over primary A2M.
- `BHP`: source pack misclassified retrieved local news as context-only; pre-fix ranking favored broad ASX 200 linked items despite abundant primary BHP articles.
- `CSL`: source pack misclassified retrieved local news as context-only; pre-fix ranking favored scan-list linked items over primary CSL article.
- `XRO`: source pack misclassified retrieved local news as context-only; pre-fix ranking favored scan-list linked items over primary XRO article.
- `NST`: source pack misclassified retrieved local news as context-only; ranking still has broad linked resources coverage risk.
- `MIN`: source pack misclassified retrieved local news as context-only; pre-fix ranking favored broad ASX market wraps over primary MIN article.
- `COH`: `DATA_MISSING` in current Qdrant corpus for this ticker; no code-only store repair allowed.
- `WOW`: `DATA_MISSING` in current Qdrant corpus for this ticker; no code-only store repair allowed.

## SSE And Non-Stream

Both non-stream and SSE paths call `_build_ui_sources`, `_build_chat_ui_metadata`, `apply_local_news_only_guard`, and `apply_visible_evidence_gap_labels`. The source-pack change is shared by both paths.
