---
job_id: extraction_broad_residual_noncandidate_filter_v1_20260601
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_broad_residual_noncandidate_filter_v1_20260601.md
  - docs/claude/STATE.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - financial-engine_v2/scripts/test_broad_extraction_test.py
  - reports/agent_jobs/extraction_broad_residual_noncandidate_filter_v1_20260601/README.md
  - reports/agent_jobs/extraction_broad_residual_noncandidate_filter_v1_20260601/status.json
  - reports/agent_jobs/extraction_broad_residual_noncandidate_filter_v1_20260601/validation.json
  - reports/agent_jobs/extraction_broad_residual_noncandidate_filter_v1_20260601/diff-check.json
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_broad_residual_noncandidate_filter_v1_20260601
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: none
operator_approval_source: Continuation of the full extraction hardening goal after runtime sample 4bde51ce exposed residual non-candidate source-document classes.
---

# Extraction Broad Residual Noncandidate Filter V1

## Objective

Harden the next non-runtime blockers from
`extraction_broad_robustness_after_candidate_scale_followup_v1_20260601`:

1. Exclude AGM result notices that use the title abbreviation `AGM`.
2. Exclude non-financial drilling/programme-results announcements without
   formal Appendix or financial-statement evidence.
3. Exclude monthly fund/performance reports that lack formal Appendix or
   financial-statement evidence.
4. Exclude standalone ASX shareholder-summary/additional-ASX-information
   documents that lack formal Appendix or financial-statement evidence.

This is a bounded source-document classification and candidate-filter slice.
It is not a runtime sample, canary, broad backfill, gold accuracy run, or full
extraction graduation.

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

Why safe: the classifier only blocks document classes that source inspection
shows are not formal financial reports or Appendix cash-flow reports. Formal
Appendix and financial-statement markers remain explicit allow signals.

GPU process check required: no. This task must not spawn, restart, or depend on
llama-server.

## Validation

- Validate this task card.
- List active jobs and check overlap before claim.
- Focused source-document classifier tests.
- Focused broad candidate-filter helper test.
- Full touched test files if focused tests pass.
- Targeted Ruff and `py_compile`.
- Exact title probe for LM8/LSR/LSF/OLY residual failures.
- No-runtime `/data/asx/docs` candidate inventory probe.
- `git diff --check` and `git diff --cached --check`.
- `check-diff` for this task card.
- Registry release after commit.
