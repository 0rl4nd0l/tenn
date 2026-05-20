---
job_id: news_retrieval_parity_a2m_integration_v1_20260520
lane: Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/news_retrieval_parity_a2m_integration_v1_20260520.md
  - financial-engine_v2/backend/app/services/hybrid_retriever.py
  - financial-engine_v2/backend/app/services/tenn_chat.py
  - financial-engine_v2/backend/tests/test_rag_news_ticker_filter.py
  - financial-engine_v2/backend/tests/test_news_retrieval_eval.py
  - reports/agent_jobs/news_retrieval_parity_a2m_integration_v1_20260520/
  - reports/agent_jobs/news_retrieval_parity_a2m_integration_v1_20260520/README.md
  - reports/agent_jobs/news_retrieval_parity_a2m_integration_v1_20260520/diff-check.json
approval_required: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/news_retrieval_parity_a2m_integration_v1_20260520
mutation_mode: safe_extension
production_data_access: false
allow_unapproved_safe_extension: true
---

# Task

Integrate the already validated A2M news retrieval parity fix from the isolated safe-extension worktree into the active NVMe runtime baseline.

# Source Patch

- Worktree: `/home/l4nd0/tenn-news-retrieval-parity-a2m-v1-20260520`
- Branch: `safe/news-retrieval-parity-a2m-v1-20260520`
- Commit: `29ca31340ac6`
- Commit subject: `fix(query): align news ticker-list retrieval parity`

# Scope

Integrate only the retrieval parity behavior from the isolated commit. Backend news retrieval must match the requested ticker against scalar `ticker`, scalar `primary_ticker`, and list/string `tickers`.

Do not redesign retrieval behavior. Do not broaden retrieval beyond the isolated commit. Do not touch ingestion, Qdrant loaders, entity maps, news backfills, runtime, memory, Home, parser/extraction, or financial truth.

# Required Preflight

Run and report:

- `cd /home/l4nd0/tenn-runtime`
- `readlink -f /home/l4nd0/tenn-runtime`
- `git branch --show-current`
- `git rev-parse --short=12 HEAD`
- `git status --short`
- `git worktree list`
- `git show --stat --oneline --no-renames HEAD`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/news_retrieval_parity_a2m_integration_v1_20260520.md`
- `python3 scripts/agent_job_registry.py list-active --repo-root /home/l4nd0/tenn-runtime`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/news_retrieval_parity_a2m_integration_v1_20260520.md --repo-root /home/l4nd0/tenn-runtime`

Claim the registry job only if safe.

# Hard Stops

Stop before integration if:

- active registry shows overlapping Query Orchestration / news retrieval / Qdrant / source-label work;
- `/home/l4nd0/tenn-runtime` has source-code dirt beyond known untracked task/report artifacts;
- target branch is not `migration/clean-runtime-baseline-reconstruct-v1`;
- target HEAD is not at or after `669bff1c7e4f`;
- isolated commit `29ca31340ac6` cannot be found;
- integration would touch files outside the allowed list;
- patch conflicts in a way that requires redesign;
- validation cannot be run.

# Integration Method

Inspect the isolated commit before applying:

- `git show --name-status --oneline --no-renames 29ca31340ac6`
- `git show --stat --oneline --no-renames 29ca31340ac6`

If the commit contains only the allowed source/test files plus isolated task/report artifacts, integrate only:

- `financial-engine_v2/backend/app/services/hybrid_retriever.py`
- `financial-engine_v2/backend/app/services/tenn_chat.py`
- `financial-engine_v2/backend/tests/test_rag_news_ticker_filter.py`
- `financial-engine_v2/backend/tests/test_news_retrieval_eval.py`
- this integration task card
- this integration report artifacts

Do not integrate the isolated task/report artifacts unless explicitly needed for reference.

# Patch Invariants

- Backend news retrieval matches the requested ticker against scalar `ticker`, scalar `primary_ticker`, and list/string `tickers`.
- Unrelated ticker payloads are still rejected.
- ASX docs scalar ticker filtering remains unchanged.
- No Qdrant loader or payload write path changes.
- No entity map or alias changes.
- No source-label relaxation.
- No Home/news route conflation.
- No live chat persistence.

# Validation

Run:

- Focused parity/source-label tests:
  - `financial-engine_v2/backend/tests/test_rag_news_ticker_filter.py`
  - selected relevant tests from `financial-engine_v2/backend/tests/test_news_retrieval_eval.py` if direct selection is simple
- Full relevant news/source-label test set:
  - `financial-engine_v2/backend/tests/test_rag_news_ticker_filter.py`
  - `financial-engine_v2/backend/tests/test_news_retrieval_eval.py`
  - `financial-engine_v2/backend/tests/test_rag_news_query.py`
  - `financial-engine_v2/backend/tests/test_sources.py`
  - `financial-engine_v2/backend/tests/test_build_ui_sources.py`
  - `financial-engine_v2/backend/tests/test_rag_payload_guardrails.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/news_retrieval_parity_a2m_integration_v1_20260520.md`

Use the repo venv if available.

Do not run news ingestion, Qdrant loader, Qdrant resync, backfills, live Cockpit chat, Home producers, memory cleanup, parser/extraction, runtime/model/GPU changes, or service restarts.

# Required Report

Write:

`reports/agent_jobs/news_retrieval_parity_a2m_integration_v1_20260520/README.md`

Include confirmed facts, inferred facts, DATA_MISSING, source isolated commit/worktree, files integrated, diff summary, validation commands and exact results, source-label preservation evidence, whether validation matches the isolated patch, whether source files were the only non-report files changed, commit hash if committed, final git status, registry release status, and Project Memory save recommendation.
