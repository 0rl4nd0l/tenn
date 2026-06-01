---
job_id: extraction_broad_failure_source_classification_v1_20260601
lane: Evaluation
supporting_lanes:
  - Financial Truth
  - Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_broad_failure_source_classification_v1_20260601.md
  - docs/claude/STATE.md
  - reports/agent_jobs/extraction_broad_failure_source_classification_v1_20260601/README.md
  - reports/agent_jobs/extraction_broad_failure_source_classification_v1_20260601/status.json
  - reports/agent_jobs/extraction_broad_failure_source_classification_v1_20260601/validation.json
  - reports/agent_jobs/extraction_broad_failure_source_classification_v1_20260601/diff-check.json
  - reports/agent_jobs/extraction_broad_failure_source_classification_v1_20260601/source_metadata.json
  - reports/agent_jobs/extraction_broad_failure_source_classification_v1_20260601/failure_classification.json
  - reports/agent_jobs/extraction_broad_failure_source_classification_v1_20260601/source_snippets.md
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 1800
output_dir: reports/agent_jobs/extraction_broad_failure_source_classification_v1_20260601
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: none
---

# Extraction Broad Failure Source Classification V1

## Objective

Classify the five validation-gate failures from the bounded broad robustness
sample by source-document type and source-unit evidence before any follow-up
candidate-selection or Scale Policy implementation.

This is an audit-only evidence slice. It must not run extraction, mutate
canonical data, or change parser logic.

## Session Declaration

- Agent: Codex.
- Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Branch: `migration/clean-runtime-baseline-reconstruct-v1`.
- Intended files: only this task card, `docs/claude/STATE.md`, and this report
  bundle.
- Contested surfaces touched: none from `AGENTS.md`.
- Collision risk: LOW/MEDIUM by Financial Truth evidence handling, resolved by
  exact allowlist, read-only source PDFs, and active registry claim.
- Decision: proceed in SAFE EXTENSION MODE after validation and claim, with
  audit-only source inspection and report/state writes only.

## Contract Check

- Target layer: Evaluation artifacts around Extraction, with source evidence
  read from immutable PDFs.
- Relevant rules: backend remains authoritative for canonical financial truth;
  metric extraction must not infer or substitute; source PDFs are read-only;
  audit reports do not authorize canonical writes.
- What must not change: backend routes, worker/router/runtime services,
  parser prompts, schemas, source PDFs, database/Qdrant/news/memory stores,
  Cockpit UI, GitHub state, or production data.
- Why safe: the task uses `pdftotext`/`pdfinfo` read-only against already
  sampled PDFs and writes only local report artifacts.
- GPU process check required: no. This task does not spawn, restart, or depend
  on llama-server.

## Required Inputs

Use the prior sample artifacts:

- `reports/agent_jobs/extraction_broad_robustness_sample_v1_20260601/broad_sample_results.json`
- `reports/agent_jobs/extraction_broad_robustness_sample_v1_20260601/failure_digest.json`

Classify these source PDFs:

- `/data/asx/docs/GTE/financial_performance/2025-09-11_annual-report-to-shareholders_a918a867-650e-40cb-91fc-8aa184f7379d.pdf`
- `/data/asx/docs/ARL/financial_performance/2022-10-28_results-of-meeting_f6d952b4-61a9-4525-8d6d-6016bde62530.pdf`
- `/data/asx/docs/HNG/financial_performance/2021-05-17_financial-update_b99edab3-ce8c-4560-ad33-86c4c77b2250.pdf`
- `/data/asx/docs/CAF/financial_performance/2021-08-25_appendix-4e-fy21_2676743b-c638-40d9-be60-9b8069221d14.pdf`
- `/data/asx/docs/TLS/financial_performance/2022-10-11_results-of-2022-annual-general-meeting_36c30afc-00a3-45f6-acd9-163a7519441f.pdf`

## Required Output

- Source metadata for each PDF.
- Source snippets showing document class and unit/scale evidence.
- Failure classification JSON with:
  - ticker
  - source path
  - broad sample status/error
  - document type
  - whether the document should be eligible for broad extraction candidates
  - unit/scale evidence
  - likely next workstream: candidate selection, Scale Policy/source-unit
    detection, metric ontology, or no action.
- README summary with explicit partial-goal status.
- Update `docs/claude/STATE.md`.

## Forbidden

- Backend startup, llama/router startup, GPU worker reload, extraction runtime,
  `POST /api/process/document/{document_id}`, `/api/extraction-eval/real-gold`,
  broad backfill, direct SQL, source-PDF copy/mutation, parser/prompt/schema
  changes, Qdrant or embedding writes, Cockpit UI changes, GitHub mutation,
  production data mutation, and claims of full extraction graduation.

## Required Validation

- Task-card validation and registry claim.
- `pdfinfo`/`pdftotext` availability recorded.
- Prior sample artifacts parsed successfully.
- Task-card `check-diff`.
- `git diff --check` and `git diff --cached --check`.
- Registry release after commit.
