---
job_id: news_memo_env_gated_fallback_provenance_v1
lane: Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/news_memo_env_gated_fallback_provenance_v1.md
  - scripts/backfill_missing_news_memos.py
  - scripts/load_news_to_qdrant.py
  - scripts/test_backfill_missing_news_memos.py
  - scripts/test_load_news_qdrant_preflight.py
  - financial-engine_v2/backend/app/services/news_memo_extractor.py
  - financial-engine_v2/backend/app/tasks/news_tasks.py
  - financial-engine_v2/backend/tests/test_news_memo_extractor.py
  - financial-engine_v2/backend/tests/test_news_tasks.py
  - financial-engine_v2/scripts/nightly_news.sh
  - reports/agent_jobs/news_memo_env_gated_fallback_provenance_v1/
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/news_memo_env_gated_fallback_provenance_v1
mutation_mode: safe_extension
production_data_access: false
---

# Task

Implement the next safe extension after the news memo efficiency/fallback milestone.

Primary lane:
Query Orchestration

Supporting lanes:
Provenance, Reporting, Evaluation, Memory

Mode:
SAFE EXTENSION

Goal:
Add env-gated ops/nightly fallback support and provenance-ready reporting for news memo JSON failures, without making fallback a silent frontend/default behavior.

Context:
Recent pasted result reported:
- c3609b5 made daily ingest interruption durable.
- 9aae854 decoupled memo enrichment from nightly ingest.
- 4ea8bfa constrained memo extraction output quality.
- c4ab78d bounded memo backfill dispatch.
- 9d0f80f allowed bounded batches to continue after fully observed article-level failures.
- a745162 added opt-in stronger-model JSON fallback retry.
- Latest reported 36-hour coverage: 162 eligible, 162 persisted, 0 missing, 0 read errors.
- Fallback is currently CLI opt-in via --json-error-fallback-model.
- Outstanding: no nightly NEWS_JSON_ERROR_FALLBACK_MODEL wiring, no automatic GPU/model-load preflight, no per-row model provenance, no frontend repair action.

Required preflight:
- Print branch and HEAD.
- Run git status --short.
- Run git worktree list.
- Show recent commits touching news memo files.
- Validate this task card.
- Run registry/list-active if available.
- Claim the task if safe.
- Stop and report if active locks or dirty files overlap the allowed files.

Allowed work:
1. Wire an env-gated nightly/ops fallback only when memo waiting is explicitly enabled.
   - Suggested env:
     - NEWS_WAIT_FOR_MEMOS=1
     - NEWS_JSON_ERROR_FALLBACK_MODEL=model:qwen3.5-35b-a3b-apex
   - Do not make fallback default.
   - Do not enable frontend fallback.
   - Do not silently use fallback when NEWS_WAIT_FOR_MEMOS is unset/false.

2. Add model/runtime preflight before fallback if there is an existing safe probe path.
   - Confirm requested fallback model is available or fail clearly.
   - Confirm the failure mode is JSON parse / "No valid JSON found".
   - Do not add heavy model-load orchestration if it requires broad runtime changes.
   - If a clean preflight is not feasible in this scope, report DATA_MISSING and add a clear TODO/report entry.

3. Add or extend summary/provenance reporting.
   - Ensure summary JSON records primary model, fallback model, fallback attempted, fallback completed, fallback failures, and fallback reason.
   - If per-row memo model provenance can be added safely within existing memo schema/storage, do it.
   - If schema/storage migration is required, do not perform it in this job; report as a separate follow-up.

4. Add tests.
   - Fake-Celery or mocked task test where primary qwen2.5 fails with JSON parse error and fallback qwen3.5 succeeds.
   - Test that fallback does not trigger for infrastructure/pending/unobserved failures.
   - Test that fallback does not trigger unless env/CLI option is explicitly set.
   - Test that final summary status/coverage is correct after fallback success.
   - Preserve existing bounded dispatch behavior.

Do not touch:
- Cockpit frontend.
- Qdrant schema or production collections.
- Live news databases.
- Company memory.
- Market memory.
- Financial truth.
- Extraction/gold metric systems.
- Broad runtime/router/model management beyond a small preflight check.
- Any files outside allowed_files.

Hard stops:
- HIGH collision risk.
- Dirty/untracked overlapping files not owned by this task.
- Need for production data mutation.
- Need for DB schema migration.
- Need for frontend changes.
- Need to change canonical financial truth or memory stores.
- Fallback would become silent default behavior.

Validation:
Run the narrowest relevant checks, including:
- Ruff on changed Python files.
- py_compile on changed scripts/modules.
- Focused pytest for backfill/news memo/news task tests.
- CLI help probe for scripts/backfill_missing_news_memos.py.
- Shell syntax check for financial-engine_v2/scripts/nightly_news.sh if touched.
- git diff --check.
- agent job contract/check-diff if available.

Definition of done:
- Env-gated fallback path exists or is explicitly reported DATA_MISSING/blocked.
- Fallback remains opt-in.
- Summary/provenance reporting is improved.
- Tests cover primary failure -> fallback success and no-fallback cases.
- No frontend behavior changed.
- No production data mutated.
- Final report written under reports/agent_jobs/news_memo_env_gated_fallback_provenance_v1/.

Final report must include:
- Branch / HEAD.
- Task card path.
- Registry claim/release status if available.
- Files changed.
- Exact tests/checks run and results.
- What was implemented.
- What was deliberately not implemented.
- DATA_MISSING.
- Remaining risks.
- Worktree status.
- Save recommendation.
