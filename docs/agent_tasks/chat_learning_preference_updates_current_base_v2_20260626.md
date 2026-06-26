---
job_id: chat_learning_preference_updates_current_base_v2_20260626
lane: Query Orchestration
supporting_lanes:
  - Evaluation
  - Reporting
  - Provenance
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/chat_learning_preference_updates_current_base_v2_20260626
mutation_mode: safe_extension
production_data_access: false
issue: 254
allowed_files:
  - docs/agent_tasks/chat_learning_preference_updates_current_base_v2_20260626.md
  - docs/architecture/20_chat_learning_loop.md
  - financial-engine_v2/backend/app/services/tests/test_chat_preference_updater.py
  - reports/agent_jobs/chat_learning_preference_updates_current_base_v2_20260626/README.md
  - reports/agent_jobs/chat_learning_preference_updates_current_base_v2_20260626/STATE.md
  - reports/agent_jobs/chat_learning_preference_updates_current_base_v2_20260626/VALIDATION.md
  - reports/agent_jobs/chat_learning_preference_updates_current_base_v2_20260626/status.json
  - reports/agent_jobs/chat_learning_preference_updates_current_base_v2_20260626/diff-check.json
  - reports/agent_jobs/chat_learning_preference_updates_current_base_v2_20260626/PR_BODY.md
  - reports/agent_jobs/chat_learning_preference_updates_current_base_v2_20260626/REVIEW.md
github_writes_allowed:
  - draft PR after local validation
  - issue comment after merge containment
  - issue close only after canonical merge containment
---

# Chat Learning Preference Updates Current-Base Fix

## Objective

Fix issue #254 from current canonical by making the chat-learning preference
writer state explicit. This task chooses the safe truth-label path: runtime
preference writes are inactive until a separate guarded writer is intentionally
designed and validated.

## Scope

- Supersede the dirty reference-only
  `safe/issue254-chat-learning-truth-label-v1-20260626` branch with a clean
  current-base continuation.
- Update `docs/architecture/20_chat_learning_loop.md` so it no longer claims
  live `/chat` traffic writes `chat_preferences.json`.
- Add focused preference-updater coverage proving runtime-shaped persisted
  turns cannot produce retrieval/router preferences when required bounded
  updater fields are absent.
- Record validation, PR, and issue closeout evidence in the report artifacts.

## Hard Boundaries

- No runtime/service start.
- No DB, Qdrant, Redis, news, memory store, source PDF, extraction prompt,
  parser, gold-label, model/GPU, or production-data mutation.
- No user thesis memory writes or investment thesis persistence.
- No hidden, unaudited preference writes from model output.
- No product/runtime wiring beyond the docs truth-label and focused regression
  test.
- No merge, rebase, reset, stash, branch deletion, cleanup, or parking changes.

## Required Validation

- `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /home/l4nd0/tenn-issue254-chat-learning-truth-label-current-base-v2-20260626 --topic "issue 254 chat learning truth label current base v2" --json`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/chat_learning_preference_updates_current_base_v2_20260626.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/chat_learning_preference_updates_current_base_v2_20260626.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/chat_learning_preference_updates_current_base_v2_20260626.md --repo-root .`
- `python3 scripts/agent_task_ledger.py --repo-root . validate`
- Focused preference-updater test proving runtime-shaped records without
  bounded updater fields produce no retrieval/router preferences.
- Focused docs/content check proving the architecture doc truth-labels the
  preference-writer state as inactive.
- `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt python -m pytest -c financial-engine_v2/backend/pytest.ini financial-engine_v2/backend/app/services/tests/test_chat_preference_updater.py -q`
- `uv run --with ruff ruff format --check financial-engine_v2/backend/app/services/tests/test_chat_preference_updater.py`
- `uv run --with ruff ruff check financial-engine_v2/backend/app/services/tests/test_chat_preference_updater.py`
- `python3 -m py_compile financial-engine_v2/backend/app/services/tests/test_chat_preference_updater.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/chat_learning_preference_updates_current_base_v2_20260626.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/chat_learning_preference_updates_current_base_v2_20260626.md --repo-root .`

## Definition Of Done

- The selected state is explicit: runtime preference writes are inactive.
- Architecture documentation no longer overstates adaptive chat learning from
  `/chat` traffic.
- Focused validation proves runtime-shaped quality turns cannot produce
  learned preferences without required bounded fields.
- No forbidden surfaces are changed.
- Local validation and GitHub checks pass.
- PR is merged into `migration/clean-runtime-baseline-reconstruct-v1` and merge
  commit containment is verified before issue #254 is closed.
