# news_memo_env_gated_fallback_provenance_v1 Final Report

Lane: Query Orchestration
Execution mode: SAFE EXTENSION
Collision risk: LOW after moving to isolated clean worktree

## Branch / HEAD

- Branch: `codex/news-memo-env-gated-fallback-provenance-v1`
- Starting HEAD: `13fd78de7ccb`
- Saved commit: `ebae61336f9a`
- Worktree: `/mnt/sdb2/home/l4nd0/tenn-news-memo-env-gated-fallback-provenance-v1`
- Task card: `docs/agent_tasks/news_memo_env_gated_fallback_provenance_v1.md`

## Registry

- Initial claim in the shared dirty worktree was blocked by unrelated dirty file `docs/agent_tasks/metric_extraction_current_state_audit_v1.md`.
- Created isolated worktree `/mnt/sdb2/home/l4nd0/tenn-news-memo-env-gated-fallback-provenance-v1`.
- Claim succeeded for `news_memo_env_gated_fallback_provenance_v1`.
- Claim released successfully after commit.
- Active overlapping job observed: `metric_extraction_current_state_audit_v1`, lane `Evaluation`, files limited to its metric task/report paths.
- No overlapping active locks on this job's allowed files.

## Files Changed

- `docs/agent_tasks/news_memo_env_gated_fallback_provenance_v1.md`
- `scripts/backfill_missing_news_memos.py`
- `scripts/load_news_to_qdrant.py`
- `scripts/test_backfill_missing_news_memos.py`
- `scripts/test_load_news_qdrant_preflight.py`
- `financial-engine_v2/backend/app/services/news_memo_extractor.py`
- `financial-engine_v2/backend/tests/test_news_memo_extractor.py`
- `financial-engine_v2/scripts/nightly_news.sh`
- `reports/agent_jobs/news_memo_env_gated_fallback_provenance_v1/final_report.md`

## Implemented

1. Env-gated fallback in the memo backfill CLI:
   - `NEWS_JSON_ERROR_FALLBACK_MODEL` is honored only when `--wait-for-memos` is set.
   - `--json-error-fallback-model` now requires `--wait-for-memos`; otherwise the CLI fails clearly.
   - Fallback remains opt-in and never becomes the default path.

2. Nightly wait-mode fallback wiring:
   - `financial-engine_v2/scripts/nightly_news.sh` now routes `NEWS_WAIT_FOR_MEMOS=1` plus `NEWS_JSON_ERROR_FALLBACK_MODEL=...` through bounded memo backfill.
   - In that mode, the loader performs Qdrant and SQLite sync with `--no-dispatch-memos`, then `backfill_missing_news_memos.py` performs bounded primary dispatch plus JSON-error fallback.
   - If `NEWS_JSON_ERROR_FALLBACK_MODEL` is set without `NEWS_WAIT_FOR_MEMOS=1`, nightly logs that it is ignored.
   - `NEWS_MEMO_DISPATCH_BATCH_SIZE` controls bounded memo backfill batch size, default `25`.
   - `NEWS_JSON_ERROR_FALLBACK_LIMIT` controls fallback retry cap, default `3`.

3. Runtime/model preflight before fallback dispatch:
   - The fallback path probes the configured extraction llama.cpp runtime using the existing backend `verify_llm_models` path.
   - It resolves the requested fallback model against the runtime catalog before dispatching fallback tasks.
   - If the probe fails or the model is unavailable, fallback is skipped with `reason=fallback_model_preflight_failed`.
   - No model-load orchestration, router mutation, or new llama-server process management was added.

4. Summary/provenance reporting:
   - `json_error_fallback` summaries now include:
     - `primary_model`
     - `fallback_model`
     - `fallback_attempted`
     - `fallback_completed`
     - `fallback_failures`
     - `fallback_reason`
     - `runtime_preflight`
   - Backfill summaries now include `json_error_fallback_config`, including env var name, env model presence, selected model source, wait gating, fallback model, and fallback limit.
   - `dispatch_news_memos()` now reports `llm_model` and `llm_model_source`.
   - Memo JSONL rows now include `extraction_provenance` with component, model, URL, and article character cap.

5. Tests:
   - Added/updated tests for env fallback gating, CLI wait requirement, fallback preflight failure, primary JSON failure to fallback success, summary coverage after fallback success, dispatch model diagnostics, and persisted memo provenance.

## Deliberately Not Implemented

- No frontend/Cockpit repair action.
- No Qdrant schema, collection, or production data mutation.
- No live news database writes.
- No DB schema migration.
- No model-load orchestration or broad router/runtime management.
- No company memory or market memory schema changes.
- No financial truth or extraction/gold metric changes.
- No automatic fallback when wait mode is not explicitly enabled.

## DATA_MISSING

- No live fallback preflight was run against the current GPU runtime in this task. Validation used unit tests and CLI/shell probes only.
- Exact worker-default primary model cannot be known by the dispatching CLI unless a model is explicitly passed; summaries therefore report `worker_default` when no payload model is set. Persisted memo rows record the actual `NewsMemoExtractor` model used inside the worker process.
- No post-change live news run was executed; this task was a software safe extension only.

## Validation Run

All commands were run from `/mnt/sdb2/home/l4nd0/tenn-news-memo-env-gated-fallback-provenance-v1` using the existing original-worktree venv at `/mnt/sdb2/home/l4nd0/tenn/financial-engine_v2/.venv`.

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/news_memo_env_gated_fallback_provenance_v1.md` -> passed
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/news_memo_env_gated_fallback_provenance_v1.md` -> passed in clean worktree
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/news_memo_env_gated_fallback_provenance_v1.md` -> passed
- `/mnt/sdb2/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python -m ruff check scripts/backfill_missing_news_memos.py scripts/load_news_to_qdrant.py scripts/test_backfill_missing_news_memos.py scripts/test_load_news_qdrant_preflight.py financial-engine_v2/backend/app/services/news_memo_extractor.py financial-engine_v2/backend/app/tasks/news_tasks.py financial-engine_v2/backend/tests/test_news_memo_extractor.py financial-engine_v2/backend/tests/test_news_tasks.py` -> passed
- `PYTHONPYCACHEPREFIX=/tmp/tenn_pycache_compile /mnt/sdb2/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python -m py_compile scripts/backfill_missing_news_memos.py scripts/load_news_to_qdrant.py financial-engine_v2/backend/app/services/news_memo_extractor.py financial-engine_v2/backend/app/tasks/news_tasks.py` -> passed
- `/mnt/sdb2/home/l4nd0/tenn/financial-engine_v2/.venv/bin/pytest scripts/test_backfill_missing_news_memos.py scripts/test_load_news_qdrant_preflight.py financial-engine_v2/backend/tests/test_news_memo_extractor.py financial-engine_v2/backend/tests/test_news_tasks.py -q` -> `48 passed in 1.57s`
- `/mnt/sdb2/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python scripts/backfill_missing_news_memos.py --help` -> passed
- `bash -n financial-engine_v2/scripts/nightly_news.sh` -> passed
- `git diff --check` -> passed
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/news_memo_env_gated_fallback_provenance_v1.md` -> passed, no disallowed files

## Remaining Risks

- The fallback preflight verifies catalog availability only. It does not load a model, reserve VRAM, or guarantee generation success.
- The nightly fallback path writes a separate memo backfill summary JSON alongside the main nightly summary instead of merging the two artifacts.
- Existing `reports/` paths are ignored by `.git/info/exclude`; this report must be force-added if it should be committed.

## Worktree Status After Save

- Git status is clean for tracked files.
- `reports/agent_jobs/news_memo_env_gated_fallback_provenance_v1/` remains ignored by `.git/info/exclude`; this final report exists on disk but is not part of commit `ebae61336f9a`.

## Save Recommendation

Merge or cherry-pick commit `ebae61336f9a` from branch `codex/news-memo-env-gated-fallback-provenance-v1` after review.
