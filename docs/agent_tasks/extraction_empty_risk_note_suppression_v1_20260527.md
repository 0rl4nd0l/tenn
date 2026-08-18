---
job_id: extraction_empty_risk_note_suppression_v1_20260527
lane: Provenance
supporting_lanes:
  - Financial Truth
  - Evaluation
  - Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_empty_risk_note_suppression_v1_20260527.md
  - reports/agent_jobs/extraction_empty_risk_note_suppression_v1_20260527/README.md
  - reports/agent_jobs/extraction_empty_risk_note_suppression_v1_20260527/status.json
  - reports/agent_jobs/extraction_empty_risk_note_suppression_v1_20260527/validation.json
  - reports/agent_jobs/extraction_empty_risk_note_suppression_v1_20260527/diff-check.json
  - reports/agent_jobs/extraction_empty_risk_note_suppression_v1_20260527/github_issue_96_comment.md
  - reports/agent_jobs/extraction_canary_scale_gate_and_side_effect_audit_v1_20260527/README.md
  - reports/agent_jobs/extraction_canary_scale_gate_and_side_effect_audit_v1_20260527/status.json
  - financial-engine_v2/backend/app/services/pipeline.py
  - financial-engine_v2/backend/app/models/asx_financials.py
  - financial-engine_v2/backend/tests/test_extraction_scale_gate.py
  - financial-engine_v2/backend/tests/test_pipeline_stages.py
  - docs/extraction/metric_extraction_contract.md
  - docs/architecture/12_evaluation_and_drift_monitoring.md
allowed_repo_files:
  - docs/agent_tasks/extraction_empty_risk_note_suppression_v1_20260527.md
  - reports/agent_jobs/extraction_empty_risk_note_suppression_v1_20260527/**
  - reports/agent_jobs/extraction_canary_scale_gate_and_side_effect_audit_v1_20260527/**
  - financial-engine_v2/backend/app/services/pipeline.py
  - financial-engine_v2/backend/app/models/asx_financials.py
  - financial-engine_v2/backend/tests/test_extraction_scale_gate.py
  - financial-engine_v2/backend/tests/test_extraction*.py
  - financial-engine_v2/backend/tests/test_pipeline*.py
  - docs/extraction/metric_extraction_contract.md
  - docs/architecture/12_evaluation_and_drift_monitoring.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_empty_risk_note_suppression_v1_20260527
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: issue_comment_only
related_issue: 96
---

# Extraction Empty Risk Note Suppression

## Objective

Fix the narrow issue #96 persistence bug where an empty `ASXRiskNote` row can be
created even when `risk_note_written: 0`, without changing extraction
semantics, parser routing, prompts, gold labels, canonical truth promotion,
runtime configuration, source PDFs, or running another canary/backfill.

## Session Declaration

- Agent: Codex.
- Worktree:
  `/home/l4nd0/tenn-extraction-empty-risk-note-suppression-v1-20260527`.
- Branch: `safe/extraction-empty-risk-note-suppression-v1-20260527`.
- Parent live branch: `migration/clean-runtime-baseline-reconstruct-v1`.
- Parent HEAD: `5d6322f48f45739bb3db3961d0416db0af99b932`.
- Issue: #96.
- Primary lane: Provenance.
- Supporting lanes: Financial Truth, Evaluation, and Query Orchestration.
- Intended files: this task card, this job's report artifacts, the narrow
  pipeline risk-note persistence path, and focused backend tests.
- Contested surfaces touched: risk-note persistence side effect only.
- Collision risk: MEDIUM because persistence behavior touches Provenance and
  Financial Truth visibility; use an isolated worktree and registry checks.
- Decision: proceed as SAFE EXTENSION after validation, overlap check, and
  registry claim.

## Contract Check

- Target system layer: extraction persistence for `ASXRiskNote`.
- Relevant contract rules: extraction must preserve explicit values and
  provenance, fail visibly on ambiguity, and avoid fabricating or promoting
  unsupported truth. Presence of a risk-note row must agree with narrative
  content and `risk_note_written`.
- What must not change: financial metric extraction semantics, parser routing,
  extraction prompts, gold labels, canonical truth promotion, runtime/model/GPU
  config, source PDFs, production DB/Qdrant/news/memory stores, service state,
  Cockpit UI, or schema.
- Why safe: the change only suppresses creation of an empty `ASXRiskNote` row
  when no narrative content exists. Valid narrative payloads must still persist.
- GPU process check required: no. This task does not spawn extraction, run a
  canary, start/restart services, or depend on `llama-server`.

## Required Behavior

- Do not create `ASXRiskNote` rows when narrative fields are empty and
  `confidence_narrative` is `0`.
- Preserve valid risk-note persistence when narrative content exists.
- Ensure `risk_note_written` and persisted `ASXRiskNote` rows agree.
- Do not alter financial metric extraction semantics.
- Do not alter parser routing or validation-gate behavior.
- Keep PLS `scale_unknown` abstention behavior intact.
- Keep BHP native USD/no-FX behavior unchanged.

## Audit Questions

1. Where exactly is `allow_empty=True` used for `ASXRiskNote` persistence?
2. Can empty risk-note persistence be suppressed without affecting legitimate
   risk-note writes?
3. What tests prove empty rows are suppressed?
4. What tests prove real narrative rows still persist?
5. Does `risk_note_written` remain consistent with persisted rows?

## Required Preflight

- Confirm repo path, branch, HEAD, and remote.
- Run `git status --short --untracked-files=all`.
- Run `git worktree list`.
- Check registry/list-active.
- If unrelated PR39/architecture dirt exists, create/use an isolated worktree.
- Validate this task card.
- Read the canary scale-gate audit report:
  - `reports/agent_jobs/extraction_canary_scale_gate_and_side_effect_audit_v1_20260527/README.md`
  - `reports/agent_jobs/extraction_canary_scale_gate_and_side_effect_audit_v1_20260527/status.json`
- Check overlap and claim this task card before implementation.

## Forbidden

- Running the second canary batch.
- Running broad backfill.
- Production DB writes.
- Direct SQL mutation.
- Qdrant, news, or memory mutation.
- Canonical truth promotion changes.
- Parser routing changes.
- Extraction prompt changes.
- Gold-label mutation.
- Source PDF edits, moves, or commits.
- Runtime/model/GPU config changes.
- Service restarts.
- Cockpit UI implementation.
- Schema migrations.
- Unrelated cleanup, stash, reset, delete, merge, rebase, or branch cleanup.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_empty_risk_note_suppression_v1_20260527.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/extraction_empty_risk_note_suppression_v1_20260527.md --repo-root .`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/extraction_empty_risk_note_suppression_v1_20260527.md --repo-root .`
- Focused pytest for touched tests.
- `python3 -m py_compile` for touched Python files.
- Ruff for touched Python files.
- JSON validation for report artifacts.
- `git diff --check`.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_empty_risk_note_suppression_v1_20260527.md --repo-root .`.
- Confirm no source PDFs are staged.
- Registry release and final list-active.
- Final `git status --short --untracked-files=all`.

## Final Report Requirements

- Root cause confirmation.
- Files changed.
- Tests and validation results.
- Proof empty `ASXRiskNote` rows are suppressed.
- Proof valid risk notes still persist.
- Whether the second canary batch is now safe to request.
- Remaining `DATA_MISSING`.
- Explicit statement that no broad backfill or canary was run.
- Project Memory save recommendation.
- If GitHub auth allows, comment a concise update on #96 with the report path
  and remaining `DATA_MISSING`; do not close, relabel, assign, milestone, or edit
  the issue.

## Hard Stops

- Any active registry overlap on this lane or allowed files that cannot be
  resolved.
- Any need for production DB writes, direct SQL mutation, source PDF mutation,
  Qdrant/news/memory mutation, broad backfill, or second canary batch.
- Any need to change parser routing, prompts, gold labels, canonical truth
  semantics, runtime/model/GPU config, services, Cockpit UI, or schema
  migrations.
- Any generated diff outside this task card allowlist.
