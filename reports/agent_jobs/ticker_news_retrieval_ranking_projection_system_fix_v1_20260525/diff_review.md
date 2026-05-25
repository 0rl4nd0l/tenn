# Diff Review

## Files Changed

- `docs/agent_tasks/ticker_news_retrieval_ranking_projection_system_fix_v1_20260525.md`
- `financial-engine_v2/backend/app/services/rag.py`
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/backend/tests/test_rag_news_query.py`
- `financial-engine_v2/backend/tests/test_build_ui_sources.py`
- Report artifacts in `reports/agent_jobs/ticker_news_retrieval_ranking_projection_system_fix_v1_20260525/`

## Review Findings

No blocking findings found in the changed code.

## Architecture Review

- No DB, Qdrant, or news-store mutation.
- No reindex, resync, backfill, projection rebuild, projection repair, or migration.
- No parser routing changes.
- No canonical financial truth writes.
- No Tenn memory writes.
- No runtime, model, GPU, Docker, systemd, cron, or env config edits.
- No one-off ticker alias hardcoding.
- No change to `chat_evidence_guard.py`.
- No source-label masking: no-hit, context-only, data-insufficient, missing-required, and degraded rows stay unverified.

## Residual Risks

- Running backend was not restarted and does not serve this branch's code.
- `NST` still ranks a broad linked resources scan item ahead of an older primary NST article in the code-level probe. This is still local news, not filing/document context, but it is a remaining relevance-quality risk.
- Canonical SQLite news projection remains absent by design; status reporting remains honest rather than repaired.

## Validation Summary

- Focused ranking/source-pack tests: `65 passed`.
- Guard/status/source/route parity suite: `47 passed`, with existing warnings.
- Cockpit chat stream suite: `62 passed`.
- `py_compile`: pass.
- Ruff changed backend files/tests: pass.
- `git diff --check`: pass.
- Task-card validation/check-overlap/check-diff: pass.
