---
job_id: recency_half_life_decay_publish_pr_v1_20260626
lane: Query Orchestration
supporting_lanes:
  - Evaluation
  - Reporting
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/recency_half_life_decay_publish_pr_v1_20260626
mutation_mode: safe_extension
production_data_access: false
issue: 260
allowed_files:
  - docs/agent_tasks/recency_half_life_decay_publish_pr_v1_20260626.md
  - docs/agent_tasks/recency_half_life_decay_contract_v1_20260602.md
  - financial-engine_v2/backend/app/services/commentary_decay.py
  - financial-engine_v2/backend/app/services/marketplace_price_intelligence.py
  - financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py
  - reports/agent_jobs/recency_half_life_decay_contract_v1_20260602/README.md
  - reports/agent_jobs/recency_half_life_decay_contract_v1_20260602/STATE.md
  - reports/agent_jobs/recency_half_life_decay_contract_v1_20260602/VALIDATION.md
  - reports/agent_jobs/recency_half_life_decay_contract_v1_20260602/status.json
  - reports/agent_jobs/recency_half_life_decay_contract_v1_20260602/diff-check.json
  - reports/agent_jobs/recency_half_life_decay_publish_pr_v1_20260626/README.md
  - reports/agent_jobs/recency_half_life_decay_publish_pr_v1_20260626/status.json
  - reports/agent_jobs/recency_half_life_decay_publish_pr_v1_20260626/PR_BODY.md
  - reports/agent_jobs/recency_half_life_decay_publish_pr_v1_20260626/REVIEW.md
  - reports/agent_jobs/recency_half_life_decay_publish_pr_v1_20260626/diff-check.json
github_writes_allowed:
  - push branch safe/issue260-recency-half-life-decay-v1-20260626 to origin
  - open one draft PR targeting migration/clean-runtime-baseline-reconstruct-v1
  - post one issue status comment on issue 260
forbidden_actions:
  - merge PR
  - close issue 260
  - change labels, milestones, projects, assignees, or issue title
  - mutate DB, Qdrant, Redis, news stores, memory, source PDFs, extraction prompts, gold labels, runtime state, model/GPU/service config, or production data
  - dependency install or dependency file edits
  - destructive git operations
---

# Recency Half-Life Decay Publish PR

## Objective

Publish the already validated local issue #260 fix as a draft PR.

## Scope

- Re-run focused validation for the existing local fix.
- Commit the source, test, task, and report artifacts already prepared for
  issue #260.
- Push branch `safe/issue260-recency-half-life-decay-v1-20260626`.
- Open one draft PR against `migration/clean-runtime-baseline-reconstruct-v1`.
- Post one issue #260 status comment with the draft PR link.

## Non-Goals

- Do not merge the PR.
- Do not close issue #260.
- Do not broaden recency/source-weighting behavior beyond the validated local
  half-life fix.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/recency_half_life_decay_publish_pr_v1_20260626.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/recency_half_life_decay_publish_pr_v1_20260626.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/recency_half_life_decay_publish_pr_v1_20260626.md --repo-root .`
- `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt pytest -q financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py`
- `uv run --with ruff ruff format --check financial-engine_v2/backend/app/services/commentary_decay.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py`
- `uv run --with ruff ruff check financial-engine_v2/backend/app/services/commentary_decay.py financial-engine_v2/backend/app/services/source_weighting.py financial-engine_v2/backend/app/services/marketplace_price_intelligence.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py`
- `python3 -m py_compile financial-engine_v2/backend/app/services/commentary_decay.py financial-engine_v2/backend/app/services/source_weighting.py financial-engine_v2/backend/app/services/marketplace_price_intelligence.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/recency_half_life_decay_publish_pr_v1_20260626.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/recency_half_life_decay_publish_pr_v1_20260626.md --repo-root .`

## Done Criteria

- Draft PR exists for issue #260.
- Issue #260 has a status comment linking the draft PR.
- Registry claim is released.
- Ledger has a `pr_opened` entry.
- Issue remains open until canonical acceptance.
