---
job_id: extraction_pr129_ci_test_harness_second_slice_v1_20260529
lane: Evaluation
supporting_lanes:
  - Query Orchestration
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_pr129_ci_test_harness_second_slice_v1_20260529.md
  - financial-engine_v2/backend/tests/test_cockpit_api_preferences.py
  - financial-engine_v2/backend/tests/test_cockpit_conversation_continuity.py
  - financial-engine_v2/backend/tests/test_process_document_api.py
  - financial-engine_v2/cockpit/tests/test_subagents.py
  - reports/agent_jobs/extraction_pr129_ci_test_harness_second_slice_v1_20260529/README.md
  - reports/agent_jobs/extraction_pr129_ci_test_harness_second_slice_v1_20260529/status.json
  - reports/agent_jobs/extraction_pr129_ci_test_harness_second_slice_v1_20260529/diff-check.json
  - docs/claude/STATE.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/extraction_pr129_ci_test_harness_second_slice_v1_20260529
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: none
related_issue: 96
---

# Extraction PR129 CI Test Harness Second Slice V1

## Objective

Reduce the PR #129 GitHub Actions `lint-and-test` failure set with focused
test-harness repairs only, without changing production behavior or runtime
state.

## Scope

- Primary lane: Evaluation.
- Supporting lanes: Query Orchestration and Reporting.
- Mode: SAFE EXTENSION, test/report files only.
- Branch: `safe/extraction-real-gold-corpus-baseline-v1-20260529`.
- PR: #129.

## Contract Check

Target system layer: Evaluation. This task updates tests and report artifacts
only; it does not change extraction, storage, retrieval, analysis, or client
runtime behavior.

Relevant contract rules: backend remains the sole authority for extraction and
financial truth; tests must not weaken source-bound extraction guards or mask
runtime/data mutations.

What must not change: production extraction code, parser routing, prompts,
schemas, runtime/model/GPU/service config, source PDFs, DB/Qdrant/news/memory
stores, Cockpit UI, or GitHub issue state.

Why safe: fixes are limited to CI harness expectations and test doubles that
lag existing production call signatures or CI runtime behavior.

GPU process check required: no. This task does not spawn, restart, or depend on
llama-server.

## Allowed Fix Classes

- Update test expectations for response fields already returned by production
  APIs.
- Make test doubles accept the current production call signature.
- Isolate sync/celery test mode so tests do not contact Redis in CI.
- Replace event-loop access patterns that fail under the CI pytest runtime.

## Hard Stops

- Do not edit production source.
- Do not change CI workflow files.
- Do not run runtime canaries or service reloads.
- Do not mutate data stores or source PDFs.
- Do not broaden the PR beyond test-harness/report artifacts.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_pr129_ci_test_harness_second_slice_v1_20260529.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_pr129_ci_test_harness_second_slice_v1_20260529.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_pr129_ci_test_harness_second_slice_v1_20260529.md --repo-root .`
- Focused pytest for touched test files.
- Focused extraction regression pytest.
- Targeted Ruff for touched tests.
- `py_compile` for touched tests.
- JSON validation for report artifacts.
- `git diff --check`.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_pr129_ci_test_harness_second_slice_v1_20260529.md --repo-root .`
- Registry release and final status checks.

## Final Report Requirements

Report the failing CI clusters addressed, files changed, validation results,
what remains red or unverified, PR #129 check status after push, and confirm no
runtime/canary/datastore/source mutation occurred.
