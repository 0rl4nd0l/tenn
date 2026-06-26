---
job_id: recency_half_life_decay_contract_v1_20260602
lane: Query Orchestration
supporting_lanes:
  - Provenance
  - Evaluation
  - Reporting
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/recency_half_life_decay_contract_v1_20260602
mutation_mode: safe_extension
production_data_access: false
issue: 260
allowed_files:
  - docs/agent_tasks/recency_half_life_decay_contract_v1_20260602.md
  - financial-engine_v2/backend/app/services/commentary_decay.py
  - financial-engine_v2/backend/app/services/marketplace_price_intelligence.py
  - financial-engine_v2/backend/app/services/source_weighting.py
  - financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py
  - reports/agent_jobs/recency_half_life_decay_contract_v1_20260602/README.md
  - reports/agent_jobs/recency_half_life_decay_contract_v1_20260602/STATE.md
  - reports/agent_jobs/recency_half_life_decay_contract_v1_20260602/VALIDATION.md
  - reports/agent_jobs/recency_half_life_decay_contract_v1_20260602/status.json
  - reports/agent_jobs/recency_half_life_decay_contract_v1_20260602/diff-check.json
github_writes_allowed:
  - issue comment after validation
  - issue close only if acceptance criteria are fully satisfied
---

# Recency Half-Life Decay Contract

## Objective

Fix issue #260 by making `compute_recency_decay()` implement true half-life
semantics for `half_life_days`.

## Scope

- Update the centralized decay formula in
  `financial-engine_v2/backend/app/services/commentary_decay.py`.
- Add focused fixed-timestamp tests for one and two half-life intervals.
- Add source-weighting coverage for `news_article` and one longer-lived source
  type.
- Keep call-site behavior centralized through the existing helper.
- Update only directly stale source comments if they describe the old formula.
- Record validation and issue closeout evidence.

## Hard Boundaries

- No runtime/service start.
- No DB, Qdrant, Redis, news, memory, source PDF, extraction prompt, parser,
  gold-label, migration, model/GPU, or production-data mutation.
- No broad retrieval-ranking rewrites, schema changes, or source-registry data
  updates.
- No merge, rebase, reset, stash, branch deletion, or cleanup.

## Required Validation

- `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /home/l4nd0/tenn-issue260-recency-half-life-decay-v1-20260626 --topic "issue 260 recency half-life decay" --json`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/recency_half_life_decay_contract_v1_20260602.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_task_ledger.py --repo-root . validate`
- Focused fixed-time recency/source-weighting tests.
- `uv run --with ruff ruff format --check financial-engine_v2/backend/app/services/commentary_decay.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py`
- `uv run --with ruff ruff check financial-engine_v2/backend/app/services/commentary_decay.py financial-engine_v2/backend/app/services/source_weighting.py financial-engine_v2/backend/app/services/marketplace_price_intelligence.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py`
- `python3 -m py_compile financial-engine_v2/backend/app/services/commentary_decay.py financial-engine_v2/backend/app/services/source_weighting.py financial-engine_v2/backend/app/services/marketplace_price_intelligence.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/recency_half_life_decay_contract_v1_20260602.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/recency_half_life_decay_contract_v1_20260602.md --repo-root .`

## Definition Of Done

- One `half_life_days` interval decays to `0.5`; two intervals decay to
  `0.25`.
- Source weighting tests cover `news_article` and a longer-lived source type
  with fixed timestamps.
- Docs impact is recorded.
- Task ledger is updated.
- Issue #260 is commented and closed only if the evidence proves acceptance.
