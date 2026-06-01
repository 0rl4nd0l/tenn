---
job_id: extraction_pls_large_annual_report_statement_evidence_v1_20260602
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_pls_large_annual_report_statement_evidence_v1_20260602.md
  - docs/claude/STATE.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - reports/agent_jobs/extraction_pls_large_annual_report_statement_evidence_v1_20260602/README.md
  - reports/agent_jobs/extraction_pls_large_annual_report_statement_evidence_v1_20260602/status.json
  - reports/agent_jobs/extraction_pls_large_annual_report_statement_evidence_v1_20260602/validation.json
  - reports/agent_jobs/extraction_pls_large_annual_report_statement_evidence_v1_20260602/diff-check.json
approval_required: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_pls_large_annual_report_statement_evidence_v1_20260602
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: none
operator_approval_source: Continuation of the active extraction hardening goal after the 2026-06-01 broad runtime sample identified PLS-style formal annual-report statement evidence as the next blocker.
---

# Extraction PLS Large Annual Report Statement Evidence V1

## Objective

Fix the PLS-style formal annual report blocker from
`extraction_broad_runtime_after_residual_filter_v1_20260601` without running
runtime extraction or mutating canonical stores.

The specific failure is a large annual report incorporating Appendix 4E where
PyMuPDF fallback sees formal statement pages late in the PDF, but current
deterministic evidence scans miss:

1. Formal statement `$'000` / smart-apostrophe `$’000` source-unit evidence.
2. Formal statement period-end evidence such as
   `For the year ended 30 June 2023`.

This task must preserve fail-closed metric extraction: it may only use explicit
source text/table evidence and must not infer, substitute, or fabricate any
financial value.

## Session Declaration

Agent: Codex

Branch: `migration/clean-runtime-baseline-reconstruct-v1`

Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`

Lane: Financial Truth

Execution mode: SAFE EXTENSION MODE

Intended files: this task card, `docs/claude/STATE.md`, multipass extraction
service, focused multipass tests, and this report bundle.

Contested surfaces touched: none from AGENTS.md.

Collision risk: MEDIUM by financial-truth semantics; resolved by exact
allowlist, deterministic source-evidence detection only, no runtime/data-store
mutation, and focused tests.

Decision: proceed after validation, active-job check, overlap check, and
registry claim.

## Contract Check

Target system layers: Extraction and Evaluation.

Relevant contract rules: backend remains the sole authority; metric extraction
may only use explicit values; normalization may perform unit conversion but not
fabricate or fill gaps; source PDFs and stores remain read-only in this task.

What must not change: parser prompts, LLM schema, DB schema/migrations,
backend routes, runtime/canary/process-document execution, direct datastore
contents, source PDFs, Qdrant, news/memory stores, Cockpit UI, GitHub state,
and broad backfill authorization.

Why safe: the fix is deterministic evidence detection over already parsed
source text/tables, limited to formal financial-statement context. Missing or
ambiguous evidence must remain fail-closed.

GPU process check required: no. This task must not spawn, restart, or depend on
llama-server.

## Validation

- Validate this task card.
- List active jobs and check overlap before claim.
- Focused unit tests for formal-statement scale and period evidence.
- Full touched multipass test file if focused tests pass.
- Targeted Ruff and `py_compile`.
- Read-only PyMuPDF probe on the PLS source PDF to confirm deterministic scale
  and period evidence are detected.
- `git diff --check` and `git diff --cached --check`.
- `check-diff` for this task card.
- Registry release after commit.
