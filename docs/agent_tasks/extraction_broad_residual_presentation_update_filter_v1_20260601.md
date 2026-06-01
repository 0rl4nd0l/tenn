---
job_id: extraction_broad_residual_presentation_update_filter_v1_20260601
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_broad_residual_presentation_update_filter_v1_20260601.md
  - docs/claude/STATE.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - financial-engine_v2/scripts/test_broad_extraction_test.py
  - reports/agent_jobs/extraction_broad_residual_presentation_update_filter_v1_20260601/README.md
  - reports/agent_jobs/extraction_broad_residual_presentation_update_filter_v1_20260601/status.json
  - reports/agent_jobs/extraction_broad_residual_presentation_update_filter_v1_20260601/validation.json
  - reports/agent_jobs/extraction_broad_residual_presentation_update_filter_v1_20260601/diff-check.json
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_broad_residual_presentation_update_filter_v1_20260601
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: none
operator_approval_source: Continuation after post-filter runtime sample 8fd46392 exposed four residual non-candidate source classes.
---

# Extraction Broad Residual Presentation Update Filter V1

## Objective

Harden the next non-runtime blockers from
`extraction_broad_runtime_after_residual_filter_v1_20260601`:

1. Exclude AGM/annual-general-meeting presentations that lack formal Appendix or
   financial-statement evidence.
2. Exclude results-briefing notices/presentations that lack formal Appendix or
   financial-statement evidence.
3. Exclude capital-raising/placement announcements that lack formal Appendix or
   financial-statement evidence.
4. Exclude product/service launch updates that lack formal Appendix or
   financial-statement evidence.

This is a bounded source-document classification and candidate-filter slice.
It is not a runtime sample, canary, broad backfill, PLS scale fix, gold accuracy
run, or full extraction graduation.

## Session Declaration

Agent: Codex

Branch: `migration/clean-runtime-baseline-reconstruct-v1`

Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`

Lane: Financial Truth

Execution mode: SAFE EXTENSION MODE

Intended files: this task card, `docs/claude/STATE.md`, multipass extraction
service, focused multipass/broad-helper tests, and this report bundle.

Contested surfaces touched: none from AGENTS.md.

Collision risk: MEDIUM/HIGH by financial-truth semantics; resolved by exact
allowlist, deterministic source classification, no runtime/data-store
mutation, and focused tests.

Decision: proceed after validation, active-job check, overlap check, and
registry claim.

## Contract Check

Target system layers: Extraction and Evaluation.

Relevant contract rules: backend remains the sole authority; metric extraction
may only use explicit source values; source-document gates must fail closed for
non-financial/non-statement documents; source PDFs and stores are read-only in
this task.

What must not change: parser prompts, schema/migrations, backend routes,
runtime/canary/process-document execution, direct datastore contents, source
PDFs, Qdrant, news/memory stores, Cockpit UI, GitHub state, and broad backfill
authorization.

Why safe: the classifier only blocks source-inspected document classes that are
not formal financial reports or Appendix cash-flow reports. Formal Appendix,
financial-statement, and explicit A/H/Q period-report markers remain allow
signals.

GPU process check required: no. This task must not spawn, restart, or depend on
llama-server.

## Validation

- Validate this task card.
- List active jobs and check overlap before claim.
- Focused source-document classifier tests.
- Focused broad candidate-filter helper test.
- Full touched test files if focused tests pass.
- Targeted Ruff and `py_compile`.
- Exact title probe for CMM/MFG/MFD residual failures and PLS formal annual
  report retention.
- No-runtime `/data/asx/docs` candidate inventory probe.
- `git diff --check` and `git diff --cached --check`.
- `check-diff` for this task card.
- Registry release after commit.
