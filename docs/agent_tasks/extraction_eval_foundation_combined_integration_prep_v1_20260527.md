---
job_id: extraction_eval_foundation_combined_integration_prep_v1_20260527
lane: Evaluation
supporting_lanes:
  - Financial Truth
  - Provenance
  - Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_eval_foundation_combined_integration_prep_v1_20260527.md
  - docs/agent_tasks/extraction_payload_scorecard_builder_v1_20260526.md
  - docs/agent_tasks/extraction_contract_parity_guard_v1_20260526.md
  - docs/agent_tasks/extraction_source_asset_manifest_metadata_safe_extension_v1_20260526.md
  - docs/agent_tasks/extraction_terminal_state_candidate_manifest_v1_20260527.md
  - financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py
  - financial-engine_v2/backend/tests/eval_source_assets/README.md
  - financial-engine_v2/backend/tests/eval_source_assets/confirmed_metric_coverage_source_assets.json
  - reports/agent_jobs/extraction_eval_foundation_combined_integration_prep_v1_20260527/README.md
  - reports/agent_jobs/extraction_eval_foundation_combined_integration_prep_v1_20260527/status.json
  - reports/agent_jobs/extraction_eval_foundation_combined_integration_prep_v1_20260527/diff-check.json
  - reports/agent_jobs/extraction_eval_foundation_combined_integration_prep_v1_20260527/validation.json
  - reports/agent_jobs/extraction_payload_scorecard_builder_v1_20260526/README.md
  - reports/agent_jobs/extraction_payload_scorecard_builder_v1_20260526/status.json
  - reports/agent_jobs/extraction_payload_scorecard_builder_v1_20260526/payload_scorecard_sample.json
  - reports/agent_jobs/extraction_payload_scorecard_builder_v1_20260526/diff-check.json
  - reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/README.md
  - reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/status.json
  - reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/metric_contract_parity_matrix.json
  - reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/validation.json
  - reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/diff-check.json
  - reports/agent_jobs/extraction_source_asset_manifest_metadata_safe_extension_v1_20260526/README.md
  - reports/agent_jobs/extraction_source_asset_manifest_metadata_safe_extension_v1_20260526/status.json
  - reports/agent_jobs/extraction_source_asset_manifest_metadata_safe_extension_v1_20260526/source_asset_resolution_sample.json
  - reports/agent_jobs/extraction_source_asset_manifest_metadata_safe_extension_v1_20260526/validation.json
  - reports/agent_jobs/extraction_source_asset_manifest_metadata_safe_extension_v1_20260526/diff-check.json
  - reports/agent_jobs/extraction_terminal_state_candidate_manifest_v1_20260527/README.md
  - reports/agent_jobs/extraction_terminal_state_candidate_manifest_v1_20260527/status.json
  - reports/agent_jobs/extraction_terminal_state_candidate_manifest_v1_20260527/terminal_extraction_candidate_manifest.json
  - reports/agent_jobs/extraction_terminal_state_candidate_manifest_v1_20260527/terminal_extraction_candidate_manifest.csv
  - reports/agent_jobs/extraction_terminal_state_candidate_manifest_v1_20260527/validation.json
  - reports/agent_jobs/extraction_terminal_state_candidate_manifest_v1_20260527/diff-check.json
allowed_repo_files:
  - docs/agent_tasks/extraction_eval_foundation_combined_integration_prep_v1_20260527.md
  - docs/agent_tasks/extraction_payload_scorecard_builder_v1_20260526.md
  - docs/agent_tasks/extraction_contract_parity_guard_v1_20260526.md
  - docs/agent_tasks/extraction_source_asset_manifest_metadata_safe_extension_v1_20260526.md
  - docs/agent_tasks/extraction_terminal_state_candidate_manifest_v1_20260527.md
  - reports/agent_jobs/extraction_eval_foundation_combined_integration_prep_v1_20260527/**
  - reports/agent_jobs/extraction_payload_scorecard_builder_v1_20260526/**
  - reports/agent_jobs/extraction_contract_parity_guard_v1_20260526/**
  - reports/agent_jobs/extraction_source_asset_manifest_metadata_safe_extension_v1_20260526/**
  - reports/agent_jobs/extraction_terminal_state_candidate_manifest_v1_20260527/**
  - financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py
  - financial-engine_v2/backend/tests/eval_source_assets/**
  - financial-engine_v2/backend/tests/eval_fixtures/**
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_eval_foundation_combined_integration_prep_v1_20260527
mutation_mode: safe_extension
production_data_access: false
related_issues:
  - 96
  - 97
  - 98
  - 99
---

# Extraction Evaluation Foundation Combined Integration Prep

## Objective

Prepare an integration-ready combined extraction evaluation branch by
reconciling the four validated safe-extension commits for #97, #98, #99, and
#96 into one conflict-resolved branch. This branch is for canonical integration
review only and must not mutate the canonical branch.

## Lane

- Primary lane: Evaluation.
- Supporting lanes: Financial Truth, Provenance, and Query Orchestration.
- Mode: SAFE EXTENSION / INTEGRATION PREP ONLY.
- Risk: MEDIUM.

## Session Declaration

- Agent: Codex.
- Worktree:
  `/home/l4nd0/tenn-extraction-eval-foundation-combined-v1-20260527`.
- Branch: `safe/extraction-eval-foundation-combined-v1-20260527`.
- Base canonical branch: `migration/clean-runtime-baseline-reconstruct-v1`.
- Intended files: this task card, the four source task cards and report bundles,
  the combined scorecard helper, focused scorecard tests, source-asset metadata
  fixtures, and this job's report artifacts.
- Contested surfaces touched: none.
- Collision risk: MEDIUM until registry overlap checks pass because the
  scorecard helper/test are shared by the four source jobs.
- Decision: proceed only in the isolated worktree after task-card validation,
  overlap check, and registry claim.

## Source Commits

- #97 payload scorecard builder:
  `bb833aa8f916806e7151d0a49a094592644db418`.
- #98 contract parity guard:
  `d08a3e96d61d8315491f5efbea61134bbd7735f6`.
- #99 source asset manifest/resolver:
  `8f87683c87306267d8280704bf6a0116f4183096`.
- #96 terminal extraction candidate manifest:
  `2f7af32d81d677dfd4eb213bc140c005b5b79e35`.

## Contract Check

- Target system layer: Evaluation/reporting helpers around extraction
  measurement and candidate triage.
- Relevant contract rules: backend remains the source of truth; metric
  extraction must not infer, substitute, fabricate, or promote report-local
  artifacts to canonical truth; no duplicate production pipeline, parser route,
  prompt path, datastore mutation, retrieval path, runtime change, or service
  restart is introduced.
- What must not change: production extraction/backfill, production DB writes,
  Qdrant/news/memory stores, canonical financial truth, parser routing,
  extraction prompts, gold labels, source PDFs, persisted schemas, runtime/model
  or GPU config, services, and Cockpit UI.
- Why safe: the integration branch combines already validated safe-extension
  helper/report artifacts into one reviewable branch, uses synthetic tests, and
  does not run extraction or persistence.
- GPU process check required: no. This task does not spawn, restart, stop, or
  depend on `llama-server`.

## Required Behavior

- Preserve `build_confirmed_metric_payload_scorecard()` and explicit payload
  result classes from #97.
- Preserve `build_metric_contract_parity_matrix()` and `MetricContractStatus`
  from #98.
- Preserve metadata-only source asset manifest/resolver helpers and the tracked
  source asset manifest from #99.
- Preserve terminal extraction candidate manifest classes/helpers from #96.
- Keep source asset reviewability separate from extraction correctness.
- Keep payload scoreability separate from terminal extraction state.
- Keep all features report-local/eval-only.
- Preserve source task cards and report artifacts for traceability.

## Hard Stops

- Stop if canonical branch mutation is required.
- Stop if conflicts require broad product/runtime/parser/prompt/gold-label
  changes.
- Stop if implementation requires broad extraction, backfill, production DB
  writes, Qdrant/news/memory mutation, canonical truth writes, source PDF edits
  or commits, runtime/model/GPU changes, service restarts, Cockpit UI changes,
  persisted schema changes, or unrelated cleanup/stash/reset/delete operations.
- Stop if active registry jobs overlap the allowed files.
- Stop if generated diffs escape this task-card allowlist.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_eval_foundation_combined_integration_prep_v1_20260527.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_eval_foundation_combined_integration_prep_v1_20260527.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_eval_foundation_combined_integration_prep_v1_20260527.md --repo-root .`
- `python3 -m py_compile financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py`
- Focused pytest for
  `financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py`.
- Ruff on touched Python files if available.
- JSON validation for generated report artifacts.
- Raw PDF staging check.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_eval_foundation_combined_integration_prep_v1_20260527.md --repo-root .`
- Registry release and final `list-active`.
- Final `git status --short --untracked-files=all`.

## Final Report Requirements

- Base canonical HEAD.
- Combined branch name and final HEAD.
- Source commits reconciled.
- Conflict cause and resolution summary.
- Files changed.
- Validation commands and exact results.
- Confirmed / Inferred / Speculative / DATA_MISSING.
- Whether the branch is ready for canonical integration review.
- Whether any source commit should be superseded by the combined branch.
- Final git status.
- Project Memory save recommendation.
