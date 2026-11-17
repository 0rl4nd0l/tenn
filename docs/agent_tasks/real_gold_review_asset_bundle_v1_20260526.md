---
job_id: real_gold_review_asset_bundle_v1_20260526
lane: Provenance
supporting_lanes:
  - Evaluation
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/real_gold_review_asset_bundle_v1_20260526.md
  - financial-engine_v2/backend/tests/eval_source_assets/README.md
  - financial-engine_v2/backend/tests/eval_source_assets/real_gold_review_source_assets.json
  - financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py
  - reports/agent_jobs/real_gold_review_asset_bundle_v1_20260526/README.md
  - reports/agent_jobs/real_gold_review_asset_bundle_v1_20260526/status.json
  - reports/agent_jobs/real_gold_review_asset_bundle_v1_20260526/real_gold_source_asset_manifest.json
  - reports/agent_jobs/real_gold_review_asset_bundle_v1_20260526/source_asset_resolution.json
  - reports/agent_jobs/real_gold_review_asset_bundle_v1_20260526/placement_runbook.md
  - reports/agent_jobs/real_gold_review_asset_bundle_v1_20260526/off_git_bundle_status.json
  - reports/agent_jobs/real_gold_review_asset_bundle_v1_20260526/validation.json
  - reports/agent_jobs/real_gold_review_asset_bundle_v1_20260526/diff-check.json
allowed_repo_files:
  - docs/agent_tasks/real_gold_review_asset_bundle_v1_20260526.md
  - financial-engine_v2/backend/tests/eval_source_assets/**
  - financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py
  - reports/agent_jobs/real_gold_review_asset_bundle_v1_20260526/**
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/real_gold_review_asset_bundle_v1_20260526
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: issue_comment_only
related_issue: 99
---

# Real-Gold Review Asset Bundle

## Objective

Make the real-gold source PDFs reviewable from a clean checkout without
committing raw filings. This task creates a sanitized, committed manifest with
fixture-to-source bindings, file size, and SHA256 metadata, plus report-local
placement and validation evidence.

## Lane

- Primary lane: Provenance.
- Supporting lanes: Evaluation and Reporting.
- Mode: safe extension / metadata-only / report-local.

## Allowed Scope

- Create this task card and the report bundle under the configured output
  directory.
- Add or update metadata-only manifests under
  `financial-engine_v2/backend/tests/eval_source_assets/`.
- Add focused test coverage for the committed real-gold review manifest if
  needed.
- Document how a reviewer can place an approved off-git raw-PDF bundle into a
  clean checkout or mounted data root.
- Do not update `docs/claude/STATE.md` from this clean split branch because an
  active Financial Truth job currently owns that file in the shared registry.

## Forbidden

- Committing raw source PDFs or archives containing raw PDFs.
- Moving, deleting, copying, modifying, or bundling raw PDFs without explicit
  approval.
- Production extraction, canary execution, broad backfill, or live scoring.
- Production DB, Qdrant, news, memory, or canonical financial truth mutation.
- Parser routing, extraction prompt, gold-label, schema, runtime, model, GPU,
  service, or Cockpit UI changes.
- Fake or substituted source documents.
- GitHub issue mutation beyond optional issue comments.
- Unrelated cleanup, stash, reset, branch cleanup, merge, rebase, or
  cherry-pick.

## Required Behavior

- Inventory every committed real-gold fixture JSON.
- Bind each fixture to the referenced source PDF path, ticker, period type,
  period end, currency, scale, expected filename, size bytes, and SHA256.
- Verify local source existence from the current approved source-root
  candidates.
- Generate a sanitized manifest that is safe to commit and contains metadata
  only.
- Generate a report-local resolver artifact showing whether each source asset
  is present and hash/size verified on this host.
- Record that no off-git raw-PDF bundle was created unless explicit approval is
  provided.
- Keep #99 source reviewability distinct from #97 extracted-payload accuracy and
  #98 metric-family contract coverage.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/real_gold_review_asset_bundle_v1_20260526.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/real_gold_review_asset_bundle_v1_20260526.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/real_gold_review_asset_bundle_v1_20260526.md --repo-root .`
- JSON validation for committed and report-local artifacts.
- Focused pytest for source asset manifest behavior and the real-gold corpus
  asset path test with `TENN_REQUIRE_REAL_GOLD_SOURCE_ASSETS=1`.
- Raw PDF staging check.
- `git diff --check`.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/real_gold_review_asset_bundle_v1_20260526.md --repo-root .`
- Final `git status --short --untracked-files=all`.
- Registry release before closeout.

## Final Report Requirements

- Branch, HEAD, and worktree.
- Files changed.
- Current GitHub issue evidence.
- Verified source asset count and status counts.
- Tests and validations run with exact results.
- Explicit statement that no raw PDFs were committed or bundled.
- Remaining blockers for #97 broad extracted-payload scoring and #96 canary or
  backfill work.

## Hard Stops

- Any active registry overlap on allowed files that cannot be resolved.
- Any requirement to commit, move, delete, copy, modify, or bundle raw PDFs
  without explicit approval.
- Any need to mutate production data stores, canonical financial truth, model
  or runtime state, source labels, parser routing, or extraction prompts.
