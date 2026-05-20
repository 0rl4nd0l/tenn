# A2M News Trace / Entity-Linking Blast-Radius Audit v1

Date: 2026-05-19
Branch: `audit/a2m-news-trace-entity-linking-v1-20260519`
Base HEAD: `0b8c4d942be5`
Mode: `AUDIT ONLY`
Production data access: `false`

## 1. Executive Verdict

- `A2M_TRACE_PARTIAL`
- `ROOT_CAUSE_INFERRED`
- `BLAST_RADIUS_MEDIUM`
- `DATA_ACCESS_REQUIRED`

The original A2M miss is not proven to be an ingestion absence. Current static evidence points to a retrieval-selection and path-parity failure class: prior reports say ticker-filtered local retrieval could select the recall articles while broad semantic retrieval did not, and current code now preserves ticker-filtered news when it reaches chat with top-level `ticker: A2M`.

The remaining unproven piece is live storage. This audit did not have permission to query the active news SQLite DB or Qdrant. Therefore it cannot prove the current actual A2M recall article rows, entity links, Qdrant payloads, or final live ranks.

Blast radius is medium because the current `/rag/query source=news` path is list-aware (`ticker` or `tickers`), while backend chat still uses `HybridRetriever("news_chunks")` and `_filter_news_by_ticker()` paths that only match top-level `ticker`. Any multi-ticker article or article with missing/alternate `primary_ticker` can diverge between News Screen/search_news and backend chat.

## 2. Confirmed Facts

Task setup:

- `/home/l4nd0/tenn-runtime` resolves to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Runtime checkout was dirty with unrelated untracked task cards, so this audit used isolated worktree `/home/l4nd0/tenn-a2m-news-trace-audit-v1-20260519`.
- Branch is `audit/a2m-news-trace-entity-linking-v1-20260519` at `0b8c4d942be5`.
- Active Memory live-inventory worktree existed, but its allowed files are disjoint and this task did not touch memory stores or cleanup paths.
- Registry claim succeeded for this job.

Storage and projection:

- News article storage code exists in `scripts/news_pipeline/db.py`.
- It stores `articles`, `entity_links`, and `article_relevance`.
- `get_articles_for_chunk_build()` can fall back from high-precision to high-recall links when high-precision links are missing.
- `scripts/load_news_to_qdrant.py` reads `articles`, `entity_links`, and `article_relevance`, and projects Qdrant payloads with `ticker`, `tickers`, and `primary_ticker`.
- If multiple tickers exist and no primary ticker is resolved, Qdrant payload top-level `ticker` is empty while `tickers` preserves linked tickers.

A2M entity linking:

- `financial-engine_v2/config/ticker_identity_map.json` has `A2M` with canonical names `The a2 Milk Company Limited`, `The a2 Milk Company`, aliases `The a2 Milk Company`, `a2 Milk Company`, `A2 Milk`, and `news_entity_linking_enabled: true`.
- `scripts/news_pipeline/entity_linker.py` links explicit symbols (`ASX:A2M`, `ASX: A2M`, `A2M.AX`) and strict aliases such as `A2 Milk`.
- A2M-specific entity-linker tests passed.
- Qdrant payload shape tests passed, including the A2M recall payload flow from raw entity metadata to `ticker: A2M`, `primary_ticker: A2M`, and `tickers` containing `A2M`.

Retrieval routes:

- `POST /rag/query` with `source: news` calls `query_news_chunks()`.
- `query_news_chunks()` filters Qdrant `news_chunks` using either payload `ticker` or payload `tickers`.
- Cockpit News Screen posts to `/rag/query` with `source: news`.
- Cockpit `search_news` calls `ToolRouter.get_news_context()`, which prefers backend `/rag/query source=news`.
- Backend `chat_with_tenn()` retrieves news via `HybridRetriever("news_chunks")`, not through `query_news_chunks()`.
- `HybridRetriever._build_ticker_filter()` filters only payload key `ticker`.
- `tenn_chat._filter_news_by_ticker()` also only checks `chunk["ticker"]`.

Source-label behavior:

- `tenn_chat` labels local news rows `local_news_context`.
- `claim_verified` is added only when model supporting evidence matches retrieved source identifiers.
- If ticker/news was expected, retrieval was attempted, and no `local_news_context` source appears, `tenn_chat` adds `missing_required_evidence` and `no_hit`.
- `cockpit_api.py` and `query_orchestrator.py` carry `source_label_semantics_v1` and keep no-hit/missing evidence distinct from verified support.

A2M-specific prior evidence:

- `reports/a2m_ticker_news_retrieval_selection_20260506_141455/00_summary.md` says the A2M trace showed local ticker-filtered retrieval could select recall articles, while broad no-ticker semantic retrieval did not.
- That same report says synthetic A2M fixtures used audited recall metadata and proved the recall article is retained when ticker-filtered retrieval returns it.
- It also says partial entity-linking drift remained: three core recall articles were A2M-linked, while some A2 Milk recall-mention articles were not fully linked.
- The referenced older `reports/a2m_news_trace_20260506_110151` directory is not present in this checkout.

## 3. Inferred Facts

Likely original root cause:

- Not a simple missing-ingestion issue.
- More likely ticker-specific news existed but was not selected/retained because broad semantic retrieval and commentary ranking could displace it before synthesis.
- A2M-specific retrieval-selection repair was added later, but it proves the top-level ticker case, not every linked-ticker payload shape.

Likely affected retrieval path:

- Backend `chat_with_tenn()` is the highest-risk path because it does not share the exact ticker filter semantics of `/rag/query source=news`.
- News Screen and `search_news` are less exposed to the linked-tickers mismatch because they use `/rag/query source=news`.

Likely source-label risk:

- Current guards are directionally correct: missing news should be labelled `missing_required_evidence`/`no_hit`, and local news should not be `claim_verified` without support matching.
- Live source-label completeness remains unproven for the original A2M response because no live chat/report trace was available.

## 4. Speculative Claims

- The actual historical A2M recall Qdrant payload may already have top-level `ticker: A2M`; if so, current backend chat should surface it when Qdrant and embeddings are healthy.
- The actual historical A2M recall Qdrant payload may instead have only `tickers: ["A2M"]` or a different primary ticker; if so, `/rag/query` can find it while backend chat can still miss it.
- Some identity-map entries contain noisy or generic aliases, but this audit did not quantify false positives against the live corpus.

## 5. DATA_MISSING

- Current active `news_articles.sqlite` rows for A2M/A2 Milk/recall.
- Current active `entity_links` rows for the actual article IDs.
- Current active `article_relevance` rows and `primary_ticker`.
- Current active `reports/qual_context/news.sqlite` fallback rows.
- Current Qdrant `news_chunks` payloads for A2M article IDs.
- Current `/rag/query source=news` live ranks.
- Current backend `HybridRetriever("news_chunks")` live ranks.
- Original A2M chat/reporting trace.
- Missing prior `reports/a2m_news_trace_20260506_110151` report directory.
- Missing `financial-engine_v2/data/raw/asx_ticker_universe.txt`, blocking some default-universe tests.
- Missing `.cursor/rules/` architecture files in this worktree.

## 6. End-to-End Trace Map

| Stage | Owner files/functions | Evidence status | Audit result |
| --- | --- | --- | --- |
| Ingestion | `scripts/news_pipeline/ingest.py` | static only | Runs entity linker and relevance scoring during provider processing. |
| Storage | `scripts/news_pipeline/db.py` | static only | `articles`, `entity_links`, `article_relevance` are the raw evidence surfaces. |
| Entity linking | `scripts/news_pipeline/entity_linker.py`, `ticker_identity_map.json` | static confirmed for A2M aliases | Current A2M alias/symbol forms link. Live article rows unknown. |
| SQLite projection | `NewsArticleStore.get_articles_for_chunk_build()` | static only | Emits linked tickers and primary ticker; can high-recall fallback for high-precision lane gaps. |
| Qdrant projection | `scripts/load_news_to_qdrant.py` | static confirmed shape | Payload preserves `ticker`, `tickers`, `primary_ticker`; live points unknown. |
| `/rag/query` retrieval | `app/main.py`, `app/services/rag.py` | static confirmed | Matches either `ticker` or `tickers`; expands ticker candidate limit. |
| Chat retrieval | `tenn_chat.py`, `hybrid_retriever.py` | static confirmed risk | Filters only top-level `ticker`; can diverge from `/rag/query`. |
| Ranking | `rag._normalize_news_results()`, `tenn_chat._ensure_ticker_news_context()` | static confirmed | `/rag/query` boosts/dedupes; chat preserves top ticker news only after ticker-only filter. |
| Synthesis | `tenn_chat.chat_with_tenn()` | fixture confirmed | A2M fixture included when top-level ticker is A2M. |
| Source labels | `tenn_chat.py`, `cockpit_api.py`, `query_orchestrator.py` | static confirmed | No-hit/missing evidence and claim verification are separately labelled. |

## 7. A2M Trace

| Item | Status | Evidence |
| --- | --- | --- |
| A2M identity map aliases | confirmed | `ticker_identity_map.json` includes `A2 Milk` variants and `news_entity_linking_enabled: true`. |
| A2M recall fixture article | confirmed fixture only | `art_aa13edd261034dba97055d8a`, title `A2 Milk shares plunge after finding toxins in infant formula`, provider `Capital Brief`, published `2026-05-03T22:52:00Z`. |
| Current local news DB article existence | DATA_MISSING | No static SQLite news DB present; production read-only DB access not approved. |
| Current entity links for actual article IDs | DATA_MISSING | Needs read-only `entity_links` query. |
| Current article relevance / primary ticker | DATA_MISSING | Needs read-only `article_relevance` query. |
| Current Qdrant point payload | DATA_MISSING | Needs read-only Qdrant scroll/search. |
| `/rag/query` retrieval behavior | static path confirmed; live ranks missing | Code supports `ticker` or `tickers`. |
| backend chat retrieval behavior | static risk confirmed; live ranks missing | Chat path only filters top-level `ticker`. |
| synthesis inclusion | fixture confirmed for top-level ticker | Existing test keeps A2M recall source in prompt and sources. |
| source-label behavior | fixture/static confirmed; live trace missing | Existing tests cover local-news claim support and expected-news no-hit. |

## 8. Blast-Radius Analysis

Likely affected classes:

- Brand/company aliases that do not mention ticker text, such as A2M-style brand names.
- Multi-ticker articles where `tickers` contains the requested ticker but `ticker` is empty or another primary ticker.
- Noisy identity-map entries with generic aliases, especially `DME`, `PPT`, and `SHV` examples seen in current identity map.
- Common-word ticker symbols where false-positive prevention suppresses plain-token matching, such as `GOLD`, `GOOD`, `DATA`, `NOTE`, and `ASX`.
- Route parity gaps where News Screen/search_news finds a linked-ticker article but backend chat misses it.

Concrete candidate examples inspected:

- `A2M`: current aliases are strong and A2M-specific tests pass.
- `DME`: identity map includes `Dome Gold Mines` but also generic/noisy aliases like `Interactive` and `Investment`; linker filters generic single-word aliases, but map quality is still a risk.
- `PPT`: aliases include short generic/company terms such as `Perpetual`, `Vista`, and `International`.
- `SHV`: aliases include `Macquarie` and `Select Harvests`, with unrelated-looking canonical names in the map.
- `GOLD` and `GOOD`: strict entity-linker stopwords; explicit symbols are expected to be required.
- `DATA`, `NOTE`, `ASX`: not present in the identity-map lookup and are common ticker-inference stopwords.
- `COH`: not present in the identity-map lookup; not proven absent from other ticker universes.

What proves/disproves risk:

- Read-only corpus counts of articles with linked tickers but blank/different primary ticker.
- Parity tests proving `/rag/query`, `search_news`, News Screen, and `chat_with_tenn` match the same payload semantics.
- Alias fixture tests for brand/company names without ticker text.
- Negative fixture tests proving common words do not become tickers unless explicitly cued.

## 9. Prevention Plan

Add tests in the next implementation lane after the read-only live trace:

- Entity alias fixtures:
  - A2M: `A2 Milk`, `The a2 Milk Company`, `ASX:A2M`, `A2M.AX`.
  - Noisy aliases: generic one-word aliases must not high-precision link.
  - Explicit symbol forms must still link stopword-like tickers.
- Storage-to-retrieval fixtures:
  - Article with `tickers: ["A2M"]`, `primary_ticker: ""`, and top-level payload `ticker: ""` must be handled consistently by all user-facing news retrieval paths or explicitly surfaced as missing evidence.
  - Article with `ticker: "SFR"` and `tickers: ["SFR", "BHP"]` must have defined behavior for a BHP chat query.
- Ranking fixtures:
  - Ticker-filtered news must be retained above broad commentary for ticker-current-news prompts.
  - Roundup titles should not outrank direct ticker titles solely on vector score.
- Source-label/no-hit fixtures:
  - Expected local news with no local-news hit must return `missing_required_evidence` and `no_hit`.
  - Local news context without supporting evidence must not become `claim_verified`.
- Freshness fixtures:
  - Current-news query with only stale hits must be `data_insufficient` or carry a freshness warning.
- Route parity fixtures:
  - `/rag/query source=news`, ToolExecutor `search_news`, News Screen mapping, and backend `chat_with_tenn` must agree on `ticker`, `primary_ticker`, and `tickers` matching semantics.

## 10. Safe Next Task

One smallest safe next task:

`Read-only live A2M news trace with production_data_access explicitly enabled for read-only probes only.`

Scope:

- Open active `news_articles.sqlite` in SQLite read-only URI mode.
- Query A2M/A2 Milk/recall article rows and linked entity/relevance rows.
- Read-only Qdrant `news_chunks` scroll/search for matched article IDs and A2M ticker filters.
- Compare `/rag/query source=news` ticker filter semantics with backend chat `HybridRetriever("news_chunks")` ticker filter semantics without running a chat session that writes artifacts.
- Produce article IDs, payload ticker/tickers/primary_ticker, rank positions, and source-label implications.

Do not implement code until that trace proves whether the live payload problem exists.

## 11. Hard Stops / Do Not Do

- No one-off A2M alias-only fix without blast-radius coverage.
- No blind reindex/resync.
- No news ingestion or backfill.
- No Qdrant write/upsert/delete.
- No SQLite writes.
- No hidden fallback from ticker-missing to broad news in chat.
- No source-label relaxation.
- No Home/news route conflation.
- No financial-truth mutation.
- No memory mutation.

## 12. Validation Commands Run

See `validation_commands.json`.

Key results:

- Task-card validation passed.
- Registry overlap check passed before claim.
- Registry claim succeeded.
- `scripts/test_load_news_qdrant_corpus_payload.py`: 9 tests OK.
- A2M-specific entity-linker tests: 3 tests OK.
- Full `scripts/test_news_pipeline_entity_linker.py`: partial, 7 passed and 4 blocked by missing `financial-engine_v2/data/raw/asx_ticker_universe.txt`.
- Backend pytest suites were blocked because the isolated worktree has no `financial-engine_v2/.venv/bin/python`, and system `python3` has no `pytest`.

## 13. Final Git Status

`git status --short --untracked-files=all`:

```text
?? docs/agent_tasks/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519.md
```

`git status --short --untracked-files=all --ignored docs/agent_tasks/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519.md reports/agent_jobs/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519` also shows the report artifacts as ignored (`!!`) under the allowed report directory.

## 14. Registry Release Status

Released.

- `python3 scripts/agent_job_registry.py release a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519`: `ok true`
- `python3 scripts/agent_job_registry.py list-active`: `active_jobs: []`

## 15. Project Memory Save Recommendation

`SAVE_RECOMMENDED`

Reason: the audit clarified the likely failure class and blast radius, but exact current A2M DB/Qdrant rows remain `DATA_MISSING` until an approved read-only live trace runs.
