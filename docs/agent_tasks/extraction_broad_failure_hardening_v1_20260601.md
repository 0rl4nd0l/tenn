---
job_id: extraction_broad_failure_hardening_v1_20260601
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_broad_failure_hardening_v1_20260601.md
  - docs/claude/STATE.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - financial-engine_v2/scripts/broad_extraction_test.py
  - financial-engine_v2/scripts/test_broad_extraction_test.py
  - reports/agent_jobs/extraction_broad_failure_hardening_v1_20260601/README.md
  - reports/agent_jobs/extraction_broad_failure_hardening_v1_20260601/status.json
  - reports/agent_jobs/extraction_broad_failure_hardening_v1_20260601/validation.json
  - reports/agent_jobs/extraction_broad_failure_hardening_v1_20260601/diff-check.json
  - reports/agent_jobs/extraction_broad_failure_hardening_v1_20260601/code_review.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_broad_failure_hardening_v1_20260601
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: none
---

# Extraction Broad Failure Hardening V1

## Objective

Implement the bounded follow-up from
`extraction_broad_failure_source_classification_v1_20260601`:

1. Exclude AGM/poll result notices and narrow unaudited non-statement financial
   updates before broad extraction candidate selection and before backend metric
   extraction.
2. Detect raw full-dollar Appendix 4D/4E summary rows as `scale=units` when
   source values are explicitly dollar-prefixed and no scaled unit header is
   present.
3. Preserve fail-closed EBIT semantics by nulling/abstaining only the invalid
   EBIT metric when its evidence is a generic pre-tax row, instead of rejecting
   an otherwise source-valid payload.

This is a code/test hardening slice only. It does not run runtime extraction,
canary execution, broad backfill, or any datastore write.

## Session Declaration

- Agent: Codex.
- Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Branch: `migration/clean-runtime-baseline-reconstruct-v1`.
- Intended files: only this task card, `docs/claude/STATE.md`, the listed
  extraction/evaluation files and tests, and this report bundle.
- Contested surfaces touched: none from the AGENTS.md contested surface list.
- Collision risk: MEDIUM/HIGH because this touches Financial Truth extraction
  guard logic; resolved by exact allowlist, current active-registry check, no
  runtime/datastore mutation, and focused tests.
- Decision: proceed in SAFE EXTENSION MODE after validation and claim.

## Contract Check

- Target layer: backend Extraction and Evaluation helper candidate selection.
- Relevant rules: backend remains authoritative for extraction correctness;
  metric extraction must not infer or substitute values; failure ambiguity must
  surface instead of hidden fallback; source PDFs remain immutable.
- What must not change: DB/Qdrant/news/memory stores, canonical financial rows,
  source PDFs, parser routing, extraction prompts, schemas/migrations, runtime
  model/GPU config, Cockpit UI, GitHub state, or gold labels.
- Why safe: the changes are deterministic guards/unit detection on existing
  extraction payloads and report-only broad helper candidate filtering. Invalid
  EBIT evidence is nulled rather than substituted.
- GPU process check required: no. This task does not spawn, restart, stop, or
  depend on llama-server.

## Required Behavior

- `classify_source_document()` blocks AGM results/poll notices and narrow
  unaudited financial updates without formal statements.
- `broad_extraction_test.py` samples only likely financial metric candidates
  and reports excluded candidate counts/reasons.
- Appendix 4D/4E summary tables with explicit full-dollar values and no scaled
  unit header resolve to `scale=units`.
- Generic pre-tax rows do not populate canonical `ebit`; valid remaining
  metrics may pass if all other gates pass.

## Forbidden

- Runtime extraction, canary run, broad backfill, backend/worker/router start,
  `POST /api/process/document/{document_id}`, real-gold eval route execution,
  production DB writes, direct SQL mutation, Qdrant/news/memory mutation,
  source-PDF copy/mutation, parser prompt changes, schema migration, gold-label
  mutation, Cockpit UI work, GitHub mutation, and full-extraction graduation
  claims.

## Validation

- Validate and claim this task card.
- Focused pytest for touched extraction/helper tests.
- `python3 -m py_compile` for touched Python files.
- Ruff for touched Python files when available.
- `git diff --check` and staged diff check.
- Task-card `check-diff`.
- Code-review pass on modified files.
- Release registry claim after commit.
