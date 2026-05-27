---
job_id: extraction_source_asset_manifest_metadata_safe_extension_v1_20260526
lane: Provenance
supporting_lanes:
  - Evaluation
  - Financial Truth
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_source_asset_manifest_metadata_safe_extension_v1_20260526.md
  - financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py
  - financial-engine_v2/backend/tests/eval_source_assets/README.md
  - financial-engine_v2/backend/tests/eval_source_assets/confirmed_metric_coverage_source_assets.json
  - reports/agent_jobs/extraction_source_asset_manifest_metadata_safe_extension_v1_20260526/README.md
  - reports/agent_jobs/extraction_source_asset_manifest_metadata_safe_extension_v1_20260526/status.json
  - reports/agent_jobs/extraction_source_asset_manifest_metadata_safe_extension_v1_20260526/source_asset_resolution_sample.json
  - reports/agent_jobs/extraction_source_asset_manifest_metadata_safe_extension_v1_20260526/validation.json
  - reports/agent_jobs/extraction_source_asset_manifest_metadata_safe_extension_v1_20260526/diff-check.json
allowed_repo_files:
  - docs/agent_tasks/extraction_source_asset_manifest_metadata_safe_extension_v1_20260526.md
  - financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py
  - financial-engine_v2/backend/tests/eval_source_assets/**
  - reports/agent_jobs/extraction_source_asset_manifest_metadata_safe_extension_v1_20260526/**
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_source_asset_manifest_metadata_safe_extension_v1_20260526
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: issue_comment_only
related_issue: 99
---

# Extraction Source Asset Manifest Metadata Safe Extension

## Objective

Create a metadata-only source asset manifest and resolver contract for
real-gold and confirmed metric coverage source PDFs. The work enables
reviewability and testability without committing raw filings or moving local
PDFs.

## Lane

- Primary lane: Provenance.
- Supporting lanes: Evaluation and Financial Truth.
- Mode: safe_extension / metadata-report-local / test-only.

## Allowed Scope

- Create this task card and the report bundle under the configured output
  directory.
- Add a tracked metadata-only source asset manifest under
  `financial-engine_v2/backend/tests/eval_source_assets/`.
- Add resolver helper code that loads the manifest, checks local candidate path
  existence, verifies optional size/hash metadata, and reports
  present/missing/unverified states without mutating files.
- Add or update focused synthetic tests only.
- Optionally document the manifest folder purpose.

## Forbidden

- Committing raw source PDFs.
- Moving, deleting, copying, or modifying source PDFs.
- Production extraction or backfill.
- Production DB writes.
- Qdrant, news, or memory mutation.
- Canonical financial truth writes.
- Parser routing changes.
- Extraction prompt changes.
- Gold-label mutation.
- Runtime, model, GPU, or service config changes.
- Service restarts.
- Cockpit UI implementation.
- Broad schema refactors.
- Persisted database schema changes.
- Unrelated cleanup, stash, reset, delete, branch cleanup, merge, rebase, or
  cherry-pick.

## Required Preflight

- Confirm repo path and remote.
- Report branch and HEAD.
- Run `git status --short --untracked-files=all`.
- Run `git worktree list`.
- Check registry/list-active if available.
- Validate this task card.
- Check overlap against active jobs.
- Stop or use an isolated worktree if active jobs overlap allowed files.
- Read #99 audit report if available.
- Read #97 and #98 reports if available.

## Required Behavior

- Manifest format includes `asset_id`, `ticker`, `document_id` or `fixture_id`,
  expected filename/logical source name, optional `sha256`, optional
  `size_bytes`, `source_kind`, `local_candidate_paths`, `reviewability_status`,
  `missing_reason`, and `notes`.
- Resolver can load the manifest, check candidate local paths, verify optional
  hash/size metadata when files are present, report present/missing/unverified
  states, and never treat source existence as extraction correctness.
- Raw PDFs remain ignored and unstaged.
- A report-local source asset resolution artifact is emitted under the output
  directory.
- #99 reviewability stays distinct from #97 extracted payload correctness and
  #98 metric contract parity.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_source_asset_manifest_metadata_safe_extension_v1_20260526.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_source_asset_manifest_metadata_safe_extension_v1_20260526.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_source_asset_manifest_metadata_safe_extension_v1_20260526.md --repo-root .`
- Focused pytest for touched synthetic tests.
- JSON validation for generated artifacts.
- `python3 -m py_compile financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py`
- Ruff if available.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_source_asset_manifest_metadata_safe_extension_v1_20260526.md --repo-root .`
- Final `git status --short --untracked-files=all`
- Registry release before closeout.

## Final Report Requirements

- Branch, HEAD, and worktree.
- Task card path.
- Registry status.
- Files changed.
- Tests run with exact results.
- Generated artifacts.
- Confirmed / Inferred / Speculative / DATA_MISSING.
- How #99 is advanced.
- How this interacts with #97 and #98.
- What remains blocked before real-gold extracted-payload scoring can be
  trusted.
- Whether #96 broad backfill is still blocked.
- Final git status.
- Project Memory save recommendation.

## Hard Stops

- Any active registry overlap on allowed files that cannot be resolved.
- Any need to commit, move, delete, copy, or modify raw PDFs.
- Any need to mutate production data stores or canonical financial truth.
- Any need to alter parser routing, extraction prompts, gold labels, runtime
  config, services, or persisted schemas.
