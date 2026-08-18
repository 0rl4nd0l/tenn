# A2M News Projection Read-Only Smoke

Generated: 2026-05-25T13:45:28+10:00

## Executive Result

A2M is user-visible through the current live Qdrant-backed query path: both backend `http://127.0.0.1:8000/rag/query` and the Cockpit/Next rewrite `http://127.0.0.1:3000/rag/query` returned A2M news results for a read-only `source=news`, `ticker=A2M` query. This does not fix the projection-path gap: canonical NVMe SQLite projection files are absent, while legacy `/mnt/sdb2` SQLite files still contain A2M evidence that current canonical routes do not consume.

## Repo And Registry

- Worktree: `/home/l4nd0/tenn-a2m-news-projection-controller-v1-20260525`
- Branch: `safe/a2m-news-projection-integration-readonly-smoke-controller-v1-20260525`
- HEAD: `2d1e810bcb978cc062d5de81d2c6b6198a76b8a4`
- Safe isolation used: yes. Canonical `/home/l4nd0/tenn` had unrelated untracked task cards, so the controller ran in a clean isolated worktree from canonical HEAD.
- Registry: controller claimed successfully. Active non-owned jobs observed: `reporting_ui_safe_issue_fixes_v1_20260525` and `strategy_lab_quantdinger_repeatability_harness_v1_20260525`; both were file-disjoint from this smoke.
- Smoke card standalone `check-overlap`: blocked only by the active controller owning the smoke files and by the dirty controller card, so the smoke was run under the controller claim rather than as a nested claim.

## Confirmed

- Qdrant `news_chunks` is reachable on `127.0.0.1:6333`, status green, with `points_count=22324` and `indexed_vectors_count=22346`.
- Qdrant A2M count is still 24 using a combined `ticker` / `primary_ticker` / `tickers` filter. Counts: `ticker=A2M` 16, `primary_ticker=A2M` 16, `tickers contains A2M` 24.
- Backend `/api/health` returns `{"status":"ok"}` and backend `/rag/query` returned A2M news results.
- Cockpit/Next is serving from `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/cockpit-ui`; `/api/cockpit/config` is reachable and reports `features.rag=true`.
- Next `/rag/query` rewrite returned the same A2M news results as backend `/rag/query`.
- Canonical NVMe projection files are absent: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/reports/qual_context/news_articles.sqlite` and `news.sqlite` both returned `test -e` status `1`.
- Legacy `/mnt/sdb2/home/l4nd0/tenn/reports/qual_context/news_articles.sqlite` exists and has 2,983 articles, 7 distinct A2M article-relevance rows, 6 primary A2M article rows, and latest A2M publication `2026-05-17T22:01:00Z`.
- Legacy `/mnt/sdb2/home/l4nd0/tenn/reports/qual_context/news.sqlite` exists and has 24,096 context chunks, 43 ticker-like A2M chunks, 771 title/text-like A2M chunks, and 791 combined A2M-like chunks.
- Qdrant has `0` points for legacy A2M article `art_f249f18234a438ab0f84e6cb`, confirming Qdrant and legacy SQLite are not parity-equivalent.
- Cockpit has no current `api/cockpit/news/status` or `api/cockpit/status` route on the running Next server; both returned 404.

## Inferred

- The user-facing news search path can access some A2M evidence now because live backend and Next `/rag/query` calls returned A2M results.
- The projection-path problem is not an alias/entity-linking problem: A2M is present in Qdrant payload ticker fields and in legacy SQLite relevance metadata.
- The remaining user-facing gap is status/provenance clarity, not immediate A2M query reachability: the UI/config can say RAG is enabled, but it does not distinguish Qdrant retrieval health from missing canonical SQLite projection health.

## Speculative

- A full parity fix may require a later projection rebuild or data repair, but this smoke did not approve or run any rebuild, resync, backfill, ingestion, DB copy, or Qdrant mutation.

## DATA_MISSING

- Exact live chat synthesis behavior for an A2M prompt is not proven. Chat was not invoked because chat/session paths may write state.
- The intended future canonical SQLite projection source path remains unapproved.
- No route-level status contract currently proves canonical SQLite projection health to the user.

## Validation

- Smoke task-card validation: pass.
- Qdrant read-only collection/count/scroll: pass.
- SQLite read-only queries used `sqlite3 -readonly` plus `PRAGMA query_only=ON`.
- Backend `/api/health`: pass.
- Backend and Next `/rag/query`: pass.
- Forbidden mutation observed: none.

## Recommended Next Task

Run `a2m_news_projection_status_reporting_safe_extension_v1_20260525` next. Reason: the live query route can retrieve A2M from Qdrant, while the unresolved gap is that status/reporting does not distinguish Qdrant availability, missing canonical SQLite projection files, and legacy SQLite provenance. This next task must stay file-bounded and non-data-mutating.
