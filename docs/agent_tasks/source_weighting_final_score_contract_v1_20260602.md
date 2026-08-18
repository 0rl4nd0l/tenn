---
job_id: source_weighting_final_score_contract_v1_20260602
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
output_dir: reports/agent_jobs/source_weighting_final_score_contract_v1_20260602
mutation_mode: safe_extension
production_data_access: false
issue: 259
allowed_files:
  - docs/agent_tasks/source_weighting_final_score_contract_v1_20260602.md
  - financial-engine_v2/backend/app/services/source_weighting.py
  - financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py
  - reports/agent_jobs/source_weighting_final_score_contract_v1_20260602/README.md
  - reports/agent_jobs/source_weighting_final_score_contract_v1_20260602/STATE.md
  - reports/agent_jobs/source_weighting_final_score_contract_v1_20260602/VALIDATION.md
  - reports/agent_jobs/source_weighting_final_score_contract_v1_20260602/status.json
  - reports/agent_jobs/source_weighting_final_score_contract_v1_20260602/diff-check.json
github_writes_allowed:
  - issue comment after validation
  - issue close only if acceptance criteria are fully satisfied
---

# Source Weighting Final Score Contract

## Objective

Fix issue #259 by resolving the `source_weighting.apply_source_weighting()`
final-score contract so missing explicit credibility does not accidentally square
the default source weight when source weight and credibility are the same
dimension.

## Scope

- Repair `financial-engine_v2/backend/app/services/source_weighting.py`.
- Add focused tests in
  `financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py` covering:
  default `news_article`, default `youtube_transcript`, default
  `framework_pdf`, and explicit `credibility_weight` override.
- Preserve provenance and recency behavior outside the formula contract.
- Record validation and issue closeout evidence.

## Hard Boundaries

- No runtime/service start.
- No DB, Qdrant, Redis, news, memory, source PDF, extraction prompt, parser,
  gold-label, migration, model/GPU, or production-data mutation.
- No broad retrieval-ranking rewrite or unrelated chat behavior change.
- No merge, rebase, reset, stash, branch deletion, or cleanup.

## Required Validation

- `python3 /home/l4nd0/.agents/skills/tenn-git-guard/scripts/tenn_git_guard.py preflight --repo-root /home/l4nd0/tenn-issue259-source-weighting-final-score-v1-20260626 --topic "issue 259 source_weighting final_score contract" --json`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/source_weighting_final_score_contract_v1_20260602.md`
- `python3 scripts/agent_job_registry.py list-active --read-only --repo-root .`
- `python3 scripts/agent_task_ledger.py --repo-root . validate`
- Focused `test_tenn_chat_and_weighting.py` scoring tests.
- Focused retrieval/news regression if validation identifies a local ranking
  harness inside the allowed surface.
- `uv run --with ruff ruff format --check financial-engine_v2/backend/app/services/source_weighting.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py`
- `uv run --with ruff ruff check financial-engine_v2/backend/app/services/source_weighting.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py`
- `python3 -m py_compile financial-engine_v2/backend/app/services/source_weighting.py financial-engine_v2/backend/tests/test_tenn_chat_and_weighting.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/source_weighting_final_score_contract_v1_20260602.md --repo-root .`
- `python3 scripts/agent_job_contract.py check-report-artifacts docs/agent_tasks/source_weighting_final_score_contract_v1_20260602.md --repo-root .`

## Definition Of Done

- The formula decision is explicit in code/tests: default source weight is the
  resolved credibility dimension unless explicit credibility is provided.
- Missing explicit credibility no longer squares the default source weight.
- Focused validation passes or blockers are documented.
- Docs impact is recorded.
- Task ledger is updated.
- Issue #259 is commented and closed only if the evidence proves acceptance.
