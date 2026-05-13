---
job_id: news_memo_signal_routing_candidate_fixture_integration_v1
lane: Memory
owner: Codex
allowed_files:
  - docs/agent_tasks/news_memo_signal_routing_candidate_fixture_integration_v1.md
  - docs/agent_tasks/news_memo_signal_routing_candidate_fixture_v1.md
  - financial-engine_v2/backend/tests/test_memo_extractors_signal_routing.py
  - reports/agent_jobs/news_memo_signal_routing_candidate_fixture_v1/final_report.md
  - reports/agent_jobs/news_memo_signal_routing_candidate_fixture_v1/status.json
  - reports/agent_jobs/news_memo_signal_routing_candidate_fixture_v1/diff-check.json
  - reports/agent_jobs/news_memo_signal_routing_candidate_fixture_integration_v1/final_report.md
  - reports/agent_jobs/news_memo_signal_routing_candidate_fixture_integration_v1/status.json
  - reports/agent_jobs/news_memo_signal_routing_candidate_fixture_integration_v1/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 1800
output_dir: reports/agent_jobs/news_memo_signal_routing_candidate_fixture_integration_v1
mutation_mode: safe_extension
production_data_access: false
---

# Task

Integrate the isolated news memo signal-routing fixture commit into preserve without touching unrelated dirty LLM/task-card work.

Primary lane:
Memory

Supporting lanes:
Query Orchestration, Evaluation

Mode:
SAFE EXTENSION / INTEGRATION

Source implementation:
- Worktree: /mnt/sdb2/home/l4nd0/tenn-news-memo-signal-routing-candidate-fixture-v1
- Branch: codex/news-memo-signal-routing-candidate-fixture-v1
- Commit: 0e5e7df9d155
- Commit subject: milestone(memory): update news memo signal-routing ticker fixture

Goal:
Land the test-fixture repair on preserve and prove the news memo signal-routing backend failures are cleared.

Required preflight:
1. Print branch and HEAD.
2. Run `git status --short --untracked-files=all`.
3. Run `git worktree list`.
4. Run `git log --oneline -8`.
5. Run registry/list-active if available.
6. Validate this task card.
7. Inspect the source commit:
   `git show --stat --oneline --name-status 0e5e7df9d155`
8. Confirm it only touches allowed files.
9. Check whether dirty files overlap the allowed files.

Known unrelated dirty files to avoid:
- `scripts/run_llama_server.sh`
- `docs/agent_tasks/cockpit_upgrade_integration_readiness_20260509.md`
- `docs/agent_tasks/eval_instrumentation_dirty_worktree_audit_20260509.md`

Hard stops:
- Stop if dirty files overlap `financial-engine_v2/backend/tests/test_memo_extractors_signal_routing.py`.
- Stop if source commit touches production code.
- Stop if cherry-pick conflicts.
- Stop if registry shows overlapping active jobs.
- Do not stage, reset, remove, or modify unrelated dirty files.

Allowed work:
1. Cherry-pick or fast-forward integrate commit `0e5e7df9d155`.
2. Preserve the source report artifacts if task-card checks permit.
3. Write an integration report under:
   `reports/agent_jobs/news_memo_signal_routing_candidate_fixture_integration_v1/`.

Validation:
Run:
- `financial-engine_v2/.venv/bin/pytest financial-engine_v2/backend/tests/test_memo_extractors_signal_routing.py -q`
- `financial-engine_v2/.venv/bin/pytest financial-engine_v2/backend/tests/test_news_memo_extractor.py financial-engine_v2/backend/tests/test_news_tasks.py scripts/test_backfill_missing_news_memos.py scripts/test_load_news_qdrant_preflight.py -q`
- The exact previous failing subset if practical, or at minimum rerun the two signal-routing failures.
- Ruff on the changed test file if applicable.
- `git diff --check`.
- task-card check-diff if available.

Definition of done:
- Commit `0e5e7df9d155` is integrated or task stops with a clear collision report.
- The two signal-routing tests pass on preserve.
- Focused news memo tests pass on preserve.
- No production code changed.
- Strict ticker allowlist remains intact.
- Unrelated dirty LLM/task-card files are untouched.
- Final report written.

Final report must include:
- starting branch / HEAD
- final branch / HEAD
- source commit inspected
- files changed
- tests/checks and exact results
- unrelated dirty files left untouched
- DATA_MISSING
- final git status
- save recommendation
