---
job_id: extraction_terminal_state_candidate_manifest_v1_20260527
lane: Query Orchestration
supporting_lanes:
  - Evaluation
  - Financial Truth
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_terminal_state_candidate_manifest_v1_20260527.md
  - financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py
  - reports/agent_jobs/extraction_terminal_state_candidate_manifest_v1_20260527/README.md
  - reports/agent_jobs/extraction_terminal_state_candidate_manifest_v1_20260527/status.json
  - reports/agent_jobs/extraction_terminal_state_candidate_manifest_v1_20260527/terminal_extraction_candidate_manifest.json
  - reports/agent_jobs/extraction_terminal_state_candidate_manifest_v1_20260527/terminal_extraction_candidate_manifest.csv
  - reports/agent_jobs/extraction_terminal_state_candidate_manifest_v1_20260527/validation.json
  - reports/agent_jobs/extraction_terminal_state_candidate_manifest_v1_20260527/diff-check.json
allowed_repo_files:
  - docs/agent_tasks/extraction_terminal_state_candidate_manifest_v1_20260527.md
  - financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py
  - financial-engine_v2/backend/tests/eval_fixtures/**
  - financial-engine_v2/backend/tests/eval_source_assets/**
  - reports/agent_jobs/extraction_terminal_state_candidate_manifest_v1_20260527/**
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_terminal_state_candidate_manifest_v1_20260527
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: issue_comment_only
related_issue: 96
---

# Extraction Terminal State Candidate Manifest

## Objective

Create a report-local terminal extraction candidate manifest for PDF-path
documents that lack handled current-version extraction. The manifest classifies
documents for future operator review without running broad extraction, mutating
production data, writing canonical truth, or changing parser/runtime behavior.

## Lane

- Primary lane: Query Orchestration.
- Supporting lanes: Evaluation, Financial Truth, and Provenance.
- Mode: safe_extension / report-local / manifest-only.

## Session Declaration

- Agent: Codex.
- Worktree:
  `/home/l4nd0/tenn-extraction-terminal-state-candidate-manifest-v1-20260527`.
- Branch: `safe/extraction-terminal-state-candidate-manifest-v1-20260527`.
- Issue: #96.
- Intended files: this task card, a narrow report-local helper in
  `extraction_gold_eval_scorecard.py`, focused synthetic tests, and this job's
  report artifacts.
- Contested surfaces touched: none.
- Collision risk: MEDIUM before registry/overlap checks because the helper file
  is shared by recent evaluation/provenance jobs; LOW after isolated worktree,
  no active registry jobs, and successful overlap check.
- Decision: proceed only after validation, overlap check, and registry claim.

## Contract Check

- Target system layer: Query orchestration/evaluation metadata around extraction
  backlog triage. It does not alter ingestion, extraction, storage, retrieval,
  analysis, or client runtime behavior.
- Relevant contract rules: backend remains the source of truth; extraction
  must not infer, substitute, or fabricate; no duplicate production pipeline,
  parser route, prompt path, canonical write, datastore mutation, retrieval
  path, model/runtime change, or service restart is introduced.
- What must not change: production extraction/backfill, DB/Qdrant/news/memory
  stores, canonical financial truth, parser routing, extraction prompts, gold
  labels, source PDFs, persisted schemas, runtime/model/GPU/service config, and
  Cockpit UI.
- Why safe: the implementation consumes synthetic records or pre-existing
  report-local metadata, emits JSON/CSV artifacts, and never invokes extraction
  or persistence.
- GPU process check required: no. This task does not spawn, restart, stop, or
  depend on `llama-server`.

## Allowed Scope

- Create this task card and the report bundle under the configured output
  directory.
- Add report-local terminal-state classification helpers.
- Add or update focused synthetic tests only.
- Generate a manifest artifact from synthetic/report-local metadata only.
- Reference #97/#98/#99 report paths and preserve their distinct boundaries.

## Forbidden

- Broad production extraction or backfill.
- Production DB writes.
- Qdrant, news, or memory mutation.
- Canonical financial truth writes.
- Parser routing changes.
- Extraction prompt changes.
- Gold-label mutation.
- Source PDF edits, moves, copies, deletes, or commits.
- Runtime, model, GPU, or service config changes.
- Service restarts.
- Cockpit UI implementation.
- Persisted database schema changes.
- Model/runtime changes.
- Unrelated cleanup, stash, reset, delete, merge, rebase, or branch cleanup.

## Required Preflight

- Confirm repo path and remote.
- Report branch and HEAD.
- Run `git status --short --untracked-files=all`.
- Run `git worktree list`.
- Check registry/list-active if available.
- Validate this task card.
- Check overlap against active jobs.
- Stop or use an isolated worktree if active jobs overlap allowed files.
- Read the #96 audit report if available.
- Read the #97, #98, and #99 reports if available.

## Required Behavior

- Define terminal extraction state classes:
  `missing_host_file`, `file_exists_no_current_terminal_run`,
  `stale_extractor_version`, `completed_with_rows`,
  `completed_without_rows`, `skipped`, `failed_parser_error`,
  `queued_running_orphaned`, and `unknown_needs_audit`.
- Emit manifest rows with `document_id`, `ticker`, filing/document type when
  available, `pdf_path`, `host_file_exists`, extraction/current-version status,
  prior error/status reason, `candidate_class`, `recommended_action`,
  `required_preconditions`, `source_asset_manifest_link`, and scorecard
  readiness notes.
- Never treat source asset reviewability as extraction correctness.
- Never treat payload scoreability as terminal extraction state.
- Mark the manifest as non-authorizing for broad backfill.
- If live DB access would be required, stop or mark `DATA_MISSING`; production
  data access is not allowed for this job.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_terminal_state_candidate_manifest_v1_20260527.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_terminal_state_candidate_manifest_v1_20260527.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_terminal_state_candidate_manifest_v1_20260527.md --repo-root .`
- Focused pytest for touched synthetic tests.
- JSON validation for generated artifacts.
- `python3 -m py_compile financial-engine_v2/backend/app/services/extraction_gold_eval_scorecard.py financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py`
- Ruff if available.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_terminal_state_candidate_manifest_v1_20260527.md --repo-root .`
- Final `git status --short --untracked-files=all`.
- Registry release before closeout.

## Final Report Requirements

- Branch, HEAD, and worktree.
- Task card path.
- Registry status.
- Files changed.
- Tests run with exact results.
- Generated artifacts.
- Confirmed / Inferred / Speculative / DATA_MISSING.
- How #96 is advanced.
- How this depends on #97, #98, and #99.
- What remains blocked before any bounded canary/backfill.
- Whether operator approval is required for the next step.
- Final git status.
- Project Memory save recommendation.

## Hard Stops

- Any active registry overlap on allowed files that cannot be resolved.
- Any need to run broad extraction/backfill or mutate production/canonical data.
- Any need to alter parser routing, prompts, labels, source PDFs, runtime config,
  services, model/GPU config, Cockpit UI, or persisted schemas.
- Any generated diff outside this task card allowlist.
