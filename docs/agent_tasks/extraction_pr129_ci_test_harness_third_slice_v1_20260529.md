---
job_id: extraction_pr129_ci_test_harness_third_slice_v1_20260529
lane: Evaluation
supporting_lanes:
  - Financial Truth
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_pr129_ci_test_harness_third_slice_v1_20260529.md
  - reports/agent_jobs/extraction_pr129_ci_test_harness_third_slice_v1_20260529/**
  - docs/claude/STATE.md
  - financial-engine_v2/backend/tests/test_cockpit_marketplace_api.py
  - financial-engine_v2/backend/tests/test_marketplace_price_intelligence.py
  - financial-engine_v2/backend/tests/test_marketplace_scanner.py
  - financial-engine_v2/backend/tests/test_memo_extractors_signal_routing.py
  - financial-engine_v2/backend/tests/test_query_orchestrator.py
  - financial-engine_v2/cockpit/tests/test_agent_stress.py
  - financial-engine_v2/cockpit/tests/test_cockpit_chat_changes.py
  - financial-engine_v2/cockpit/tests/test_router_edge_cases.py
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_pr129_ci_test_harness_third_slice_v1_20260529
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: branch_push_only
related_pr: 129
---

# Extraction PR129 CI Test Harness Third Slice V1

## Objective

Fix the remaining PR #129 GitHub Actions `lint-and-test` failures that are
test-harness drift rather than extraction behavior regressions.

## Scope

Primary lane: Evaluation.

Mode: SAFE EXTENSION, test/report-only.

Branch:
`safe/extraction-real-gold-corpus-baseline-v1-20260529`.

Worktree:
`/home/l4nd0/tenn-extraction-real-gold-corpus-baseline-v1-20260529`.

## Contract Check

Target system layer: Evaluation tests and CI harness expectations.

Relevant contract rules: backend remains sole authority; metric extraction must
not infer/substitute values; no direct datastore mutation; no alternate
retrieval/extraction pipeline.

What must not change: production code, source PDFs, parser routing, extraction
prompts, gold labels, schemas/migrations, runtime/model/GPU/service config,
DB/Qdrant/news/memory stores, Cockpit UI, or canary execution.

Why safe: this task updates tests to match existing explicit guard behavior
without changing runtime behavior or canonical financial truth.

GPU process check required: no. This task does not start or depend on
llama-server.

## Hard Stops

- Do not edit production service/runtime/UI files.
- Do not restart services or run canaries.
- Do not mutate DB, Qdrant, news, memory, source PDFs, parser routing, prompts,
  schemas, runtime config, or GitHub issue state.
- Do not weaken extraction truth gates or make broad accuracy claims.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_pr129_ci_test_harness_third_slice_v1_20260529.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_pr129_ci_test_harness_third_slice_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_pr129_ci_test_harness_third_slice_v1_20260529.md --repo-root .`
- Focused local pytest reproduction for the 15 CI failures.
- Full touched test-file pytest.
- Focused extraction regression pytest suite.
- Ruff on touched files.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_pr129_ci_test_harness_third_slice_v1_20260529.md --repo-root .`
- Release registry claim and recheck active jobs.

## Final Report Requirements

Report PR #129 check state, files changed, validation commands/results,
remaining CI blockers if any, confirmation that no runtime/canary/datastore or
source mutation ran, and final git status.
