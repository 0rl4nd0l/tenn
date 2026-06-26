---
job_id: chat_session_coherence_range_v1_20260602
lane: Query Orchestration
supporting_lanes:
  - Evaluation
  - Memory
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/chat_session_coherence_range_v1_20260602
mutation_mode: safe_extension
production_data_access: false
issue: 258
allowed_files:
  - docs/agent_tasks/chat_session_coherence_range_v1_20260602.md
  - financial-engine_v2/backend/app/services/chat_quality_scorer.py
  - financial-engine_v2/backend/app/services/tests/test_chat_quality_scorer.py
  - reports/agent_jobs/chat_session_coherence_range_v1_20260602/README.md
  - reports/agent_jobs/chat_session_coherence_range_v1_20260602/STATE.md
  - reports/agent_jobs/chat_session_coherence_range_v1_20260602/VALIDATION.md
  - reports/agent_jobs/chat_session_coherence_range_v1_20260602/status.json
  - reports/agent_jobs/chat_session_coherence_range_v1_20260602/diff-check.json
github_writes_allowed:
  - issue comment after validation
  - issue close only if acceptance criteria are fully satisfied
---

# Chat Session Coherence Range

## Objective

Fix issue #258 by keeping `compute_session_coherence()` inside its documented
`0.0` to `1.0` range.

## Scope

- Clamp the raw inverted cosine score in
  `financial-engine_v2/backend/app/services/chat_quality_scorer.py`.
- Add a focused negative-cosine regression test.
- Preserve first-turn, repeated-query, related-topic, and composite scoring
  behavior.
- Record validation and issue closeout evidence.

## Hard Boundaries

- No runtime/service start.
- No DB, Qdrant, Redis, news, memory, source PDF, extraction prompt, parser,
  gold-label, migration, model/GPU, or production-data mutation.
- No broad chat retrieval, ranking, preference-learning, or route rewrites.
- No merge, rebase, reset, stash, branch deletion, or cleanup.

## Required Validation

- `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /home/l4nd0/tenn-issue258-chat-session-coherence-range-v1-20260626 --topic "issue 258 chat session coherence range" --json`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/chat_session_coherence_range_v1_20260602.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_task_ledger.py --repo-root . validate`
- Focused `test_chat_quality_scorer.py` tests for negative-cosine clamp,
  repeated query, and first-turn behavior.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/chat_session_coherence_range_v1_20260602.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/chat_session_coherence_range_v1_20260602.md --repo-root .`

## Definition Of Done

- `compute_session_coherence()` cannot return below `0.0` or above `1.0`.
- Focused tests prove the upper-bound regression and existing behaviors.
- Docs impact is recorded.
- Task ledger is updated.
- Issue #258 is commented and closed only if the evidence proves acceptance.
