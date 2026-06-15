---
job_id: extraction_source_noncandidate_preparse_gate_v1_20260615
lane: Financial Truth
supporting_lanes:
  - Evaluation
  - Provenance
  - Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/extraction_source_noncandidate_preparse_gate_v1_20260615.md
  - financial-engine_v2/backend/app/services/multipass_extraction.py
  - financial-engine_v2/backend/tests/test_multipass_extraction.py
  - reports/agent_jobs/extraction_source_noncandidate_preparse_gate_v1_20260615/README.md
  - reports/agent_jobs/extraction_source_noncandidate_preparse_gate_v1_20260615/status.json
  - reports/agent_jobs/extraction_source_noncandidate_preparse_gate_v1_20260615/validation.json
  - reports/agent_jobs/extraction_source_noncandidate_preparse_gate_v1_20260615/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/extraction_source_noncandidate_preparse_gate_v1_20260615
mutation_mode: safe_extension
allow_audit_code_changes: true
production_data_access: false
github_mutation_allowed: true
---

# Extraction Source Noncandidate Preparse Gate

## Objective

Implement one bounded production-readiness improvement for the remaining
`document_family_eligibility_noncandidate_prefilter` root-cause class: block
obvious title-only source noncandidates before parser and metric extraction
work.

## Current Evidence

- PR #346 is merged into `origin/migration/clean-runtime-baseline-reconstruct-v1`
  at `107adb03852558d42795b28c3a5ec887e7cd0c64`.
- The merged-base root-cause matrix handoff reports five remaining
  source-noncandidate documents: EQR meeting/proxy, MAH operational project
  update, FCL board-change notice, HRZ share-sale/gross-proceeds announcement,
  and MPL pre-results segment re-presentation.
- Existing code already fails these after parsing via
  `validation_gate:source_noncandidate:*`; this task moves the title-only
  subset to a pre-parser gate to reduce wasted parser/pass3a work and improve
  production readiness.

## Hard Stops

- Do not run count-24, count-32, random samples, broad extraction, broad
  replay, backfill, full ticker extraction, or service routes.
- Do not mutate DB, Qdrant, Redis, news, memory, source PDFs, prompts, gold
  labels, schema, runtime/service/model/GPU config, or production data.
- Do not relax validation gates, source ontology, period gates, scale gates, or
  metric label guards.
- Do not revisit LBL period binding except as untouched guardrail context.

## Required Implementation

- Add a focused RED regression test first proving a known title-only
  source-noncandidate is blocked before `extract_structured()` is called.
- Implement the smallest code change in `multipass_extraction.py`.
- Preserve the existing post-parse source-document classification payload shape.
- Preserve valid financial-report candidates.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/extraction_source_noncandidate_preparse_gate_v1_20260615.md`
- Focused RED test before implementation.
- Focused GREEN test after implementation.
- `python3 -m py_compile financial-engine_v2/backend/app/services/multipass_extraction.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/extraction_source_noncandidate_preparse_gate_v1_20260615.md --repo-root .`
