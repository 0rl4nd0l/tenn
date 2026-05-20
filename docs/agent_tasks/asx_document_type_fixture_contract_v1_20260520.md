---
job_id: asx_document_type_fixture_contract_v1_20260520
lane: Financial Truth
owner: Codex
mutation_mode: safe_extension
approval_required: false
allow_unapproved_safe_extension: true
allow_audit_code_changes: true
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/asx_document_type_fixture_contract_v1_20260520
allowed_files:
  - docs/agent_tasks/asx_document_type_fixture_contract_v1_20260520.md
  - docs/asx_document_type_fixture_contract.md
  - financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/
  - financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/annual_report_basic.json
  - financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/half_year_report_basic.json
  - financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/appendix_4c_quarterly_cashflow.json
  - financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/appendix_4d_half_year_results.json
  - financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/appendix_4e_preliminary_final.json
  - financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/appendix_5b_mining_cashflow.json
  - financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/other_asx_announcement_investor_presentation.json
  - financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/unknown_low_signal.json
  - financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/ambiguous_appendix_4d_4e_abstain.json
  - financial-engine_v2/backend/tests/fixtures/asx_document_type_classifier/manifest.json
  - financial-engine_v2/backend/tests/test_asx_document_type_fixture_contract.py
  - reports/agent_jobs/asx_document_type_fixture_contract_v1_20260520/
  - reports/agent_jobs/asx_document_type_fixture_contract_v1_20260520/README.md
  - reports/agent_jobs/asx_document_type_fixture_contract_v1_20260520/diff-check.json
  - reports/agent_jobs/asx_document_type_fixture_contract_v1_20260520/status.json
---

# ASX Document-Type Fixture Contract v1

Create the first safe fixture/schema contract for ASX-aware document-type
classification. This task defines small synthetic fixture shapes and expected
classifier outputs only. It does not implement a classifier or connect document
types to parser routing, extraction prompts, gold labels, canonical writes, or
financial truth persistence.

## Scope

- Add the ASX document-type fixture contract document.
- Add synthetic JSON fixtures under the backend test fixture tree.
- Add standard-library-only tests that validate fixture schema and safety
  boundaries.
- Add a report bundle for this job.

## Boundaries

Document-type classification is metadata, not metric truth. An ASX document
type does not authorize parser routing, extraction behavior changes, canonical
writes, gold-label edits, scorecard edits, or financial truth persistence.

Production data access is false. Fixture text must be short surrogate text, not
full report pages or copyrighted source excerpts.

## Required Preflight

- `cd /home/l4nd0/tenn-runtime`
- `readlink -f /home/l4nd0/tenn-runtime`
- `git branch --show-current`
- `git rev-parse --short=12 HEAD`
- `git status --short`
- `git worktree list`
- `git show --stat --oneline --no-renames HEAD`
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/asx_document_type_fixture_contract_v1_20260520.md`
- `python3 scripts/agent_job_registry.py list-active --repo-root /home/l4nd0/tenn-runtime`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/asx_document_type_fixture_contract_v1_20260520.md --repo-root /home/l4nd0/tenn-runtime`

Claim the registry only if no overlapping Financial Truth, extraction, parser,
or evaluation fixture work is active.

## Hard Stops

- Active registry shows overlapping Financial Truth, extraction, parser, or
  evaluation fixture work.
- Worktree has source-code dirt beyond known task/report artifacts.
- The task requires changing parser routing, extraction prompts, Docling
  behavior, OCR behavior, comparator behavior, or classifier implementation.
- The task requires changing existing gold labels, canonical eval scorecards,
  canonical writes, DBs, Qdrant, memory, news, runtime/model/GPU config,
  Cockpit, Home, source labels, or financial truth writes.
- The task requires production data access or live extraction.

## Validation

- `python3 -m pytest financial-engine_v2/backend/tests/test_asx_document_type_fixture_contract.py -q`
- `python3 -m json.tool` over all fixture JSON files.
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/asx_document_type_fixture_contract_v1_20260520.md`

Do not run extraction jobs, Docling, OCR, comparator tools, Qdrant, news jobs,
memory jobs, Cockpit chat, Home producers, runtime/model/GPU tests, or parser
routing checks.
