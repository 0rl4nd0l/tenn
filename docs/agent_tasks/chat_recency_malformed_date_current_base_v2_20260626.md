---
job_id: chat_recency_malformed_date_current_base_v2_20260626
lane: Query Orchestration
supporting_lanes:
  - Evaluation
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/chat_recency_malformed_date_current_base_v2_20260626.md
  - financial-engine_v2/backend/app/services/source_weighting.py
  - financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py
  - reports/agent_jobs/chat_recency_malformed_date_current_base_v2_20260626/README.md
  - reports/agent_jobs/chat_recency_malformed_date_current_base_v2_20260626/STATE.md
  - reports/agent_jobs/chat_recency_malformed_date_current_base_v2_20260626/VALIDATION.md
  - reports/agent_jobs/chat_recency_malformed_date_current_base_v2_20260626/status.json
  - reports/agent_jobs/chat_recency_malformed_date_current_base_v2_20260626/diff-check.json
  - reports/agent_jobs/chat_recency_malformed_date_current_base_v2_20260626/PR_BODY.md
  - reports/agent_jobs/chat_recency_malformed_date_current_base_v2_20260626/REVIEW.md
approval_required: true
approval_reference: "User requested safe issue fixing and closeout; PR #419 is blocked by conflicts after adjacent merges."
timeout_seconds: 14400
output_dir: reports/agent_jobs/chat_recency_malformed_date_current_base_v2_20260626
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: push_branch_open_replacement_pr_supersede_pr419_and_close_issue261_if_gated
---

# Chat Recency Malformed Date Current Base V2

## Objective

Resolve issue #261 from current canonical after PR #419 became conflicted.

## Scope

- Start from `origin/migration/clean-runtime-baseline-reconstruct-v1` at
  `26e6000ff7b02a4e05ab6a7f31f939b34aa55215`.
- Apply only the malformed `published_at` isolation behavior from the prior
  #261 branch.
- Preserve the already merged #416 recency half-life behavior and #418
  final-score credibility behavior.
- Add focused regression coverage proving malformed dates do not drop valid
  neighboring chat context.
- Publish a replacement PR for issue #261 only after validation passes.
- Close or supersede PR #419 only after the replacement path exists.
- Close issue #261 only after a replacement PR is merged and verified contained
  in canonical.

## Forbidden

- Branch deletion, pruning, reset, stash, rebase, cherry-pick, forced push, or
  unrelated cleanup.
- DB, Qdrant, Redis, news store, memory, source-document, prompt, gold-label,
  evaluator, model, GPU, or config changes.
- Label, milestone, project, or assignee changes.
- Closing issue #261 before canonical merge containment is verified.

## Validation

- `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /home/l4nd0/tenn-issue261-malformed-date-current-base-v2-20260626 --topic "issue 261 malformed date current base repair" --json`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/chat_recency_malformed_date_current_base_v2_20260626.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/chat_recency_malformed_date_current_base_v2_20260626.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/chat_recency_malformed_date_current_base_v2_20260626.md --repo-root .`
- `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py -q`
- `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/tests/test_news_retrieval_eval.py -q`
- `uv run --with ruff ruff check financial-engine_v2/backend/app/services/source_weighting.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py`
- `python3 -m py_compile financial-engine_v2/backend/app/services/source_weighting.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py`
- `git diff --check`
- `python3 -m json.tool reports/agent_jobs/chat_recency_malformed_date_current_base_v2_20260626/status.json`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/chat_recency_malformed_date_current_base_v2_20260626.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/chat_recency_malformed_date_current_base_v2_20260626.md --repo-root .`

## Hard Stops

- Task-card validation fails.
- Registry overlap shows an active conflicting job.
- Focused tests fail.
- Replacement PR checks fail or remain pending.
- PR #419 cannot be superseded without branch deletion.
