---
job_id: chat_retrieval_precision_current_base_v2_20260626
lane: Query Orchestration
supporting_lanes:
  - Evaluation
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/chat_retrieval_precision_current_base_v2_20260626.md
  - financial-engine_v2/backend/app/services/chat_quality_scorer.py
  - financial-engine_v2/backend/app/services/tests/test_chat_quality_scorer.py
  - reports/agent_jobs/chat_retrieval_precision_current_base_v2_20260626/README.md
  - reports/agent_jobs/chat_retrieval_precision_current_base_v2_20260626/STATE.md
  - reports/agent_jobs/chat_retrieval_precision_current_base_v2_20260626/VALIDATION.md
  - reports/agent_jobs/chat_retrieval_precision_current_base_v2_20260626/status.json
  - reports/agent_jobs/chat_retrieval_precision_current_base_v2_20260626/diff-check.json
  - reports/agent_jobs/chat_retrieval_precision_current_base_v2_20260626/PR_BODY.md
  - reports/agent_jobs/chat_retrieval_precision_current_base_v2_20260626/REVIEW.md
approval_required: true
approval_reference: "User requested safe issue fixing and closeout."
timeout_seconds: 14400
output_dir: reports/agent_jobs/chat_retrieval_precision_current_base_v2_20260626
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: push_branch_open_pr_and_close_issue257_if_gated
---

# Chat Retrieval Precision Current Base V2

## Objective

Fix issue #257 from current canonical by making chat retrieval precision honor
explicit `final_score` values and exclude attached-source-only chunk kinds from
the primary retrieval precision metric.

## Scope

- Repair `financial-engine_v2/backend/app/services/chat_quality_scorer.py`.
- Add focused scorer regressions in
  `financial-engine_v2/backend/app/services/tests/test_chat_quality_scorer.py`.
- Preserve query/retrieval ranking semantics outside the quality scorer metric.
- Publish and merge only after focused validation and GitHub checks pass.
- Close issue #257 only after canonical merge containment is verified.

## Forbidden

- DB, Qdrant, Redis, news, memory, source-document, prompt, parser,
  gold-label, migration, service, model, GPU, or config changes.
- Retrieval-ranking rewrites outside the scorer contract.
- Branch deletion, pruning, reset, stash, rebase, cherry-pick, forced push, or
  unrelated cleanup.
- Issue close before canonical containment is verified.

## Validation

- `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /home/l4nd0/tenn-issue257-retrieval-precision-current-base-v2-20260626 --topic "issue 257 retrieval precision current base repair" --json`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/chat_retrieval_precision_current_base_v2_20260626.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/chat_retrieval_precision_current_base_v2_20260626.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/chat_retrieval_precision_current_base_v2_20260626.md --repo-root .`
- `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/app/services/tests/test_chat_quality_scorer.py -q`
- `uv run --with ruff ruff check financial-engine_v2/backend/app/services/chat_quality_scorer.py financial-engine_v2/backend/app/services/tests/test_chat_quality_scorer.py`
- `uv run --with ruff ruff format --check financial-engine_v2/backend/app/services/chat_quality_scorer.py financial-engine_v2/backend/app/services/tests/test_chat_quality_scorer.py`
- `python3 -m py_compile financial-engine_v2/backend/app/services/chat_quality_scorer.py financial-engine_v2/backend/app/services/tests/test_chat_quality_scorer.py`
- `git diff --check`
- `python3 -m json.tool reports/agent_jobs/chat_retrieval_precision_current_base_v2_20260626/status.json`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/chat_retrieval_precision_current_base_v2_20260626.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/chat_retrieval_precision_current_base_v2_20260626.md --repo-root .`

## Done Criteria

- Explicit `final_score: 0.0` counts as a valid score.
- Missing or invalid `final_score` may fall back to `relevance_score`.
- `ephemeral` and `concat` chunks are excluded from primary retrieval precision.
- Local and GitHub validation pass.
- Issue #257 is closed only after the merged commit is verified contained in
  canonical.
