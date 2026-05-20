# News Retrieval Parity A2M Integration

Job: `news_retrieval_parity_a2m_integration_v1_20260520`

## Confirmed facts

- Target path: `/home/l4nd0/tenn-runtime`
- Resolved target: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- Target branch: `migration/clean-runtime-baseline-reconstruct-v1`
- Pre-integration target HEAD: `669bff1c7e4f`
- Pre-task-card `git status --short`: clean
- Source worktree present in `git worktree list`: `/home/l4nd0/tenn-news-retrieval-parity-a2m-v1-20260520`
- Source branch: `safe/news-retrieval-parity-a2m-v1-20260520`
- Source commit: `29ca31340ac6`
- Source commit parent: `669bff1c7e4f16a7f3f67a887ed77bd833cd5ade`
- Source commit subject: `fix(query): align news ticker-list retrieval parity`
- Source commit was found by `git cat-file -t 29ca31340ac6`: `commit`
- Task-card validation result: `ok: true`
- Registry pre-claim `list-active`: `active_jobs: []`, `ok: true`
- Registry pre-claim `check-overlap`: `ok: true`, `issues: []`
- Registry claim result: `ok: true`
- The source commit includes the four intended source/test paths plus isolated task/report artifacts.
- Integration method used: `git restore --source=29ca31340ac6 -- <four allowed source/test paths>`.
- Isolated task/report artifacts were not integrated.

## Inferred facts

- Because the source commit parent is exactly the target pre-integration HEAD, restoring the four source/test paths applies the same code/test delta as the isolated patch without conflict or redesign.
- The focused validation command collected `20` tests rather than the isolated report's `18` because this integration also selected two direct source-label preservation tests in `test_news_retrieval_eval.py`; it covered the same parity surface plus additional direct source-label assertions.
- The broad relevant news/source-label suite matches the isolated branch validation count: `114 passed`.

## DATA_MISSING

- No live SQLite or Qdrant inspection was run in this integration task.
- No live Cockpit chat smoke was run.
- No ingestion, Qdrant loader, Qdrant resync, news backfill, Home producer, memory cleanup, parser/extraction, runtime/model/GPU change, or service restart was run.
- `.cursor/rules/00_mandatory_index.md`, `.cursor/rules/backend_architecture.md`, `.cursor/rules/embedding_rules.md`, `.cursor/rules/vector_store_invariants.md`, and `.cursor/rules/failure_policy.md` are absent in this runtime checkout. Architecture review used the available checked-in architecture docs instead.
- Final commit hash and registry release status are not knowable inside this pre-commit report artifact; they are recorded in the assistant closeout after commit and release.

## Files integrated

- `financial-engine_v2/backend/app/services/hybrid_retriever.py`
- `financial-engine_v2/backend/app/services/tenn_chat.py`
- `financial-engine_v2/backend/tests/test_rag_news_ticker_filter.py`
- `financial-engine_v2/backend/tests/test_news_retrieval_eval.py`

## Diff summary

Source/test diff after transfer:

```text
financial-engine_v2/backend/app/services/hybrid_retriever.py       | 79 ++++++++++++++++--
financial-engine_v2/backend/app/services/tenn_chat.py              |  4 +-
financial-engine_v2/backend/tests/test_news_retrieval_eval.py      | 96 ++++++++++++++++++++--
financial-engine_v2/backend/tests/test_rag_news_ticker_filter.py   | 100 added
```

Behavioral summary:

- Added payload ticker normalization and matching for `ticker`, `primary_ticker`, and `tickers`.
- Updated news Qdrant filter construction to match any of `ticker`, `primary_ticker`, or `tickers`.
- Updated backend chat news filtering to use the same payload ticker matcher.
- Kept ASX docs scalar ticker filtering unchanged.
- Added tests proving linked-ticker news is retained when scalar `ticker` / `primary_ticker` belongs to another ticker.
- Added tests proving unrelated ticker payloads are still rejected.

## Validation commands and exact results

Focused parity/source-label command:

```bash
PYTHONPATH="$PWD/financial-engine_v2/backend:$PWD/financial-engine_v2" financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_rag_news_ticker_filter.py financial-engine_v2/backend/tests/test_news_retrieval_eval.py::TestNewsTickerFilter financial-engine_v2/backend/tests/test_news_retrieval_eval.py::TestChatWithTennTickerPropagation::test_linked_ticker_news_with_different_primary_is_kept_as_context_only financial-engine_v2/backend/tests/test_news_retrieval_eval.py::TestChatWithTennTickerPropagation::test_local_news_is_context_only_without_direct_support_marker financial-engine_v2/backend/tests/test_news_retrieval_eval.py::TestChatWithTennTickerPropagation::test_ticker_filtered_recall_news_is_kept_in_prompt_and_sources
```

Result:

```text
20 passed in 0.93s
```

Full relevant news/source-label command:

```bash
PYTHONPATH="$PWD/financial-engine_v2/backend:$PWD/financial-engine_v2" financial-engine_v2/.venv/bin/python -m pytest financial-engine_v2/backend/tests/test_rag_news_ticker_filter.py financial-engine_v2/backend/tests/test_news_retrieval_eval.py financial-engine_v2/backend/tests/test_rag_news_query.py financial-engine_v2/backend/tests/test_sources.py financial-engine_v2/backend/tests/test_build_ui_sources.py financial-engine_v2/backend/tests/test_rag_payload_guardrails.py
```

Result:

```text
114 passed in 2.82s
```

Diff gate command:

```bash
git diff --check
```

Result:

```text
passed with no output
```

Task-card diff gate command:

```bash
python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/news_retrieval_parity_a2m_integration_v1_20260520.md
```

Result:

```text
ok: true
disallowed_files: []
issues: []
changed_files:
- docs/agent_tasks/news_retrieval_parity_a2m_integration_v1_20260520.md
- financial-engine_v2/backend/app/services/hybrid_retriever.py
- financial-engine_v2/backend/app/services/tenn_chat.py
- financial-engine_v2/backend/tests/test_news_retrieval_eval.py
- financial-engine_v2/backend/tests/test_rag_news_ticker_filter.py
- reports/agent_jobs/news_retrieval_parity_a2m_integration_v1_20260520/README.md
- reports/agent_jobs/news_retrieval_parity_a2m_integration_v1_20260520/diff-check.json
```

## Source-label preservation evidence

- `test_linked_ticker_news_with_different_primary_is_kept_as_context_only` passed.
- `test_local_news_is_context_only_without_direct_support_marker` passed.
- `test_ticker_filtered_recall_news_is_kept_in_prompt_and_sources` passed.
- The linked A2M news fixture with `ticker: AEG`, `primary_ticker: AEG`, and `tickers: ["A2M", "AEG", "BCA", "VMM"]` is retained for A2M but remains `local_news_context` / `context_only`.
- The same fixture is not upgraded to `claim_verified` without direct supporting evidence.

## Architecture review

### Change: news retrieval ticker-list parity in backend query/chat filtering

| Rule file | Section | Status | Explanation |
|---|---|---|---|
| docs/architecture/06_embeddings_and_vector_store.md | Vector store invariants | COMPLIANT | The patch changes query-time payload filtering and score boosting only; it does not change embedding provider, vector store, collection distance, vector dimension, vector IDs, or payload write paths. |
| docs/architecture/10_failure_model.md | Failure matrix | COMPLIANT | The patch does not add fallback embedding logic, Qdrant fallback behavior, or silent degradation. |
| .cursor/rules/*.md | Mandatory architecture rules | DATA_MISSING | The architecture-check skill's named `.cursor/rules/` files are absent in this checkout. |

Summary:

- COMPLIANT: 2
- VIOLATES RULE: 0
- REQUIRES MIGRATION: 0
- DATA_MISSING: 1 rule-file set

Verdict: APPROVED within the available repo architecture docs; no migration-required invariant was touched.

## Code review

Result: no critical, warning, or suggestion findings for the transferred diff.

Review scope:

- `financial-engine_v2/backend/app/services/hybrid_retriever.py`
- `financial-engine_v2/backend/app/services/tenn_chat.py`
- `financial-engine_v2/backend/tests/test_rag_news_ticker_filter.py`
- `financial-engine_v2/backend/tests/test_news_retrieval_eval.py`

Checks covered: clarity/readability, naming, duplication, error handling, no exposed secrets/API keys, input validation, test coverage, performance.

## Non-report file boundary

- Production source changes are limited to:
  - `financial-engine_v2/backend/app/services/hybrid_retriever.py`
  - `financial-engine_v2/backend/app/services/tenn_chat.py`
- Other non-report changes are limited to:
  - integration task card
  - two test files
- No isolated A2M task/report artifacts were integrated.

## Commit and release

- Commit hash if committed: `DATA_MISSING` at report write time.
- Final git status: `DATA_MISSING` at report write time.
- Registry release status: `DATA_MISSING` at report write time.

## Project Memory save recommendation

Save a memory note after closeout: the active NVMe runtime branch integrated A2M news retrieval parity from `29ca31340ac6` by restoring only the two source and two test paths, preserving source-label behavior, avoiding ingestion/Qdrant/runtime changes, and validating with focused parity/source-label tests plus the 114-test relevant news/source-label suite.
