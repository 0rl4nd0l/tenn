---
job_id: chat_recency_malformed_date_isolation_v1_20260602
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
output_dir: reports/agent_jobs/chat_recency_malformed_date_isolation_v1_20260602
mutation_mode: safe_extension
production_data_access: false
issue: 261
allowed_files:
  - docs/agent_tasks/chat_recency_malformed_date_isolation_v1_20260602.md
  - financial-engine_v2/backend/app/services/commentary_decay.py
  - financial-engine_v2/backend/app/services/source_weighting.py
  - financial-engine_v2/backend/app/services/tenn_chat.py
  - financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py
  - reports/agent_jobs/chat_recency_malformed_date_isolation_v1_20260602/README.md
  - reports/agent_jobs/chat_recency_malformed_date_isolation_v1_20260602/STATE.md
  - reports/agent_jobs/chat_recency_malformed_date_isolation_v1_20260602/VALIDATION.md
  - reports/agent_jobs/chat_recency_malformed_date_isolation_v1_20260602/status.json
  - reports/agent_jobs/chat_recency_malformed_date_isolation_v1_20260602/diff-check.json
github_writes_allowed:
  - issue comment after validation
  - issue close only if acceptance criteria are fully satisfied
---

# Chat Recency Malformed Date Isolation

## Objective

Fix issue #261 by isolating malformed `published_at` metadata during source
recency weighting so one bad timestamp does not crash chunk weighting or the
chat strategy path.

## Scope

- Add focused source weighting and chat strategy regressions in
  `financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py`.
- Repair the smallest source surface needed to keep malformed timestamp
  provenance visible while preserving valid neighboring chunks.
- Record validation and issue closeout evidence.

## Hard Boundaries

- No runtime/service start.
- No DB, Qdrant, Redis, news, memory, source PDF, extraction prompt, parser,
  gold-label, migration, model/GPU, or production-data mutation.
- Do not silently drop malformed source metadata.
- No broad retrieval-ranking rewrite or unrelated chat behavior change.
- No merge, rebase, reset, stash, branch deletion, or cleanup.

## Required Validation

- `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /home/l4nd0/tenn-issue261-malformed-date-isolation-v1-20260626 --topic "issue 261 malformed source date isolation" --json`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/chat_recency_malformed_date_isolation_v1_20260602.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_task_ledger.py --repo-root . validate`
- Focused source weighting tests for malformed `published_at`.
- Focused chat strategy test proving valid neighboring chunks survive one
  malformed date.
- `uv run --with ruff ruff format --check financial-engine_v2/backend/app/services/source_weighting.py financial-engine_v2/backend/app/services/tenn_chat.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py`
- `uv run --with ruff ruff check financial-engine_v2/backend/app/services/source_weighting.py financial-engine_v2/backend/app/services/tenn_chat.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py`
- `python3 -m py_compile financial-engine_v2/backend/app/services/source_weighting.py financial-engine_v2/backend/app/services/tenn_chat.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/chat_recency_malformed_date_isolation_v1_20260602.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/chat_recency_malformed_date_isolation_v1_20260602.md --repo-root .`

## Definition Of Done

- Malformed `published_at` no longer crashes `apply_weighting_to_chunk()`.
- The malformed timestamp remains visible through explicit status/warning
  metadata.
- `_apply_chat_strategy()` still returns valid neighboring chunks when one chunk
  has a malformed timestamp.
- Focused validation passes.
- Docs impact is recorded.
- Task ledger is updated.
- Issue #261 is commented and closed only if the evidence proves acceptance.
