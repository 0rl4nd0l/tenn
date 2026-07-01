---
job_id: news_memo_worker_env_durable_v1_20260701
lane: Memory
supporting_lanes:
  - Evaluation
  - Memory
  - Reporting
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/news_memo_worker_env_durable_v1_20260701
mutation_mode: safe_extension
production_data_access: false
allowed_files:
  - docs/agent_tasks/news_memo_worker_env_durable_v1_20260701.md
  - financial-engine_v2/scripts/nightly_news.sh
  - financial-engine_v2/docker-compose.yml
  - scripts/load_news_to_qdrant.py
  - scripts/backfill_missing_news_memos.py
  - scripts/test_nightly_news_runtime_guard.py
  - scripts/test_load_news_qdrant_preflight.py
  - scripts/test_backfill_missing_news_memos.py
  - docs/setup/environment.md
  - docs/architecture/09_worker_and_celery_contract.md
  - reports/agent_jobs/news_memo_worker_env_durable_v1_20260701/STATE.md
  - reports/agent_jobs/news_memo_worker_env_durable_v1_20260701/VALIDATION.md
  - reports/agent_jobs/news_memo_worker_env_durable_v1_20260701/CODE_REVIEW.md
  - reports/agent_jobs/news_memo_worker_env_durable_v1_20260701/runtime_functionality_proof.md
  - reports/agent_jobs/news_memo_worker_env_durable_v1_20260701/ledger_entries.jsonl
  - reports/agent_jobs/news_memo_worker_env_durable_v1_20260701/status.json
  - reports/agent_jobs/news_memo_worker_env_durable_v1_20260701/diff-check.json
github_writes_allowed: []
---

# News Memo Worker Env Durable Fix

## Objective

Prevent nightly news memo enrichment from dispatching memo tasks that depend on
stale worktree-local output paths or implicit worker/model defaults.

## Evidence

- Prior bounded proof parked stale `llm_gpu` work and successfully dispatched one
  current news memo candidate to
  `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/reports/research_memory/news_memos.jsonl`.
- The stale queue payloads targeted missing worktree paths instead of the durable
  NVMe research memory store.
- A narrow worker run required explicit `OLLAMA_URL`, `LLAMACPP_URL`,
  `LLAMACPP_MODEL`, `LLM_API_KEY`, and durable memory-root environment.

## Scope

- Make `financial-engine_v2/scripts/nightly_news.sh` resolve a durable research
  memory root, defaulting to the NVMe store when present.
- Pass explicit memo LLM URL/model values from nightly into loader and bounded
  memo backfill dispatch.
- Add loader/backfill CLI support and focused tests for memo LLM URL/model
  propagation.
- Make compose worker profiles carry the durable env and host-path alias needed
  for host-dispatched memo payload paths.
- Update operator docs for the durable memo environment contract.
- Record validation and remaining runtime-proof status in the report bundle.

## Hard Boundaries

- Do not restore, delete, or process the parked stale Redis queue.
- Do not mutate source PDFs, Qdrant data, DB rows, gold labels, extraction
  prompts, model files, Docker volumes, service units, secrets, or GitHub.
- Do not run broad backfills. A runtime smoke is allowed only as a bounded
  current-news memo proof if validation requires it and the active queue is
  empty.
- Do not clean or absorb unrelated work in `/home/l4nd0/tenn`.

## Required Validation

- `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /home/l4nd0/tenn-news-memo-worker-env-durable-v1-20260701 --topic news_memo_worker_env_durable_v1_20260701 --json`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/news_memo_worker_env_durable_v1_20260701.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `bash -n financial-engine_v2/scripts/nightly_news.sh`
- `python3 -m unittest scripts.test_nightly_news_runtime_guard`
- Focused pytest or unittest coverage for `scripts/test_load_news_qdrant_preflight.py`
  and `scripts/test_backfill_missing_news_memos.py`.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/news_memo_worker_env_durable_v1_20260701.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/news_memo_worker_env_durable_v1_20260701.md --repo-root .`
- `git diff --check`

## Definition Of Done

- Nightly memo dispatch no longer uses a checkout-local research memory path
  when the durable NVMe store is available.
- Memo tasks dispatched by nightly/backfill include explicit LLM URL/model
  configuration.
- Compose workers expose the same durable env and path visibility needed for
  those tasks.
- Focused validation passes or blockers are documented.
- Runtime functionality proof is either `WORKING` for a bounded smoke or
  explicitly `DATA_MISSING`/`PARTIAL` if no live run is performed.
- Git status and docs impact are recorded before closeout.
