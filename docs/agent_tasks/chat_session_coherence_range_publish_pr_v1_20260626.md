---
job_id: chat_session_coherence_range_publish_pr_v1_20260626
lane: Query Orchestration
supporting_lanes:
  - Evaluation
  - Reporting
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/chat_session_coherence_range_publish_pr_v1_20260626
mutation_mode: safe_extension
production_data_access: false
issue: 258
allowed_files:
  - docs/agent_tasks/chat_session_coherence_range_publish_pr_v1_20260626.md
  - docs/agent_tasks/chat_session_coherence_range_v1_20260602.md
  - financial-engine_v2/backend/app/services/chat_quality_scorer.py
  - financial-engine_v2/backend/app/services/tests/test_chat_quality_scorer.py
  - reports/agent_jobs/chat_session_coherence_range_v1_20260602/README.md
  - reports/agent_jobs/chat_session_coherence_range_v1_20260602/STATE.md
  - reports/agent_jobs/chat_session_coherence_range_v1_20260602/VALIDATION.md
  - reports/agent_jobs/chat_session_coherence_range_v1_20260602/status.json
  - reports/agent_jobs/chat_session_coherence_range_v1_20260602/diff-check.json
  - reports/agent_jobs/chat_session_coherence_range_publish_pr_v1_20260626/README.md
  - reports/agent_jobs/chat_session_coherence_range_publish_pr_v1_20260626/status.json
  - reports/agent_jobs/chat_session_coherence_range_publish_pr_v1_20260626/PR_BODY.md
  - reports/agent_jobs/chat_session_coherence_range_publish_pr_v1_20260626/REVIEW.md
  - reports/agent_jobs/chat_session_coherence_range_publish_pr_v1_20260626/diff-check.json
github_writes_allowed:
  - push branch safe/issue258-chat-session-coherence-range-v1-20260626 to origin
  - open one draft PR targeting migration/clean-runtime-baseline-reconstruct-v1
  - post one issue #258 status comment with the draft PR link
---

# Chat Session Coherence Publish PR

## Objective

Publish the validated local fix for issue #258 as a draft PR.

## Scope

- Revalidate the existing local fix on
  `safe/issue258-chat-session-coherence-range-v1-20260626`.
- Commit only the issue #258 source/test changes, the original issue #258 task
  card/report artifacts, and this publish task/report bundle.
- Push the branch to `origin`.
- Open one draft PR targeting
  `migration/clean-runtime-baseline-reconstruct-v1`.
- Add one issue #258 status comment with the PR link.

## Hard Boundaries

- Do not merge the PR.
- Do not close issue #258.
- Do not label, milestone, assign, or Project-update issue #258 or the PR.
- Do not touch production DB, Qdrant, Redis, news, memory, source PDFs,
  extraction prompts, parser routing, gold labels, runtime/model/GPU/service
  config, dependency files, or unrelated dirty work.
- Do not reset, stash, rebase, force-push, prune, delete branches, or clean
  worktrees.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/chat_session_coherence_range_publish_pr_v1_20260626.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/chat_session_coherence_range_publish_pr_v1_20260626.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/chat_session_coherence_range_publish_pr_v1_20260626.md --repo-root .`
- `uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt pytest -q financial-engine_v2/backend/app/services/tests/test_chat_quality_scorer.py`
- `uv run --with ruff ruff format --check financial-engine_v2/backend/app/services/chat_quality_scorer.py financial-engine_v2/backend/app/services/tests/test_chat_quality_scorer.py`
- `uv run --with ruff ruff check financial-engine_v2/backend/app/services/chat_quality_scorer.py financial-engine_v2/backend/app/services/tests/test_chat_quality_scorer.py`
- `python3 -m py_compile financial-engine_v2/backend/app/services/chat_quality_scorer.py financial-engine_v2/backend/app/services/tests/test_chat_quality_scorer.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/chat_session_coherence_range_publish_pr_v1_20260626.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/chat_session_coherence_range_publish_pr_v1_20260626.md --repo-root .`

## Definition Of Done

- Focused validation is green.
- Code review finds no blocking findings.
- Intended files are committed.
- Branch is pushed.
- Draft PR is open and linked from issue #258.
- Issue #258 remains open until canonical acceptance.
