---
job_id: asx_comparator_artifact_schema_v1_20260521
lane: Financial Truth
owner: Codex
mutation_mode: safe_extension
approval_required: false
allow_unapproved_safe_extension: true
production_data_access: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/asx_comparator_artifact_schema_v1_20260521

allowed_files:
  - docs/agent_tasks/asx_comparator_artifact_schema_v1_20260521.md
  - docs/asx_comparator_artifact_schema.md
  - financial-engine_v2/backend/app/services/asx_comparator_artifact_schema.py
  - financial-engine_v2/backend/tests/test_asx_comparator_artifact_schema.py
  - reports/agent_jobs/asx_comparator_artifact_schema_v1_20260521/
  - reports/agent_jobs/asx_comparator_artifact_schema_v1_20260521/README.md
  - reports/agent_jobs/asx_comparator_artifact_schema_v1_20260521/diff-check.json
---

# ASX Comparator Artifact Schema v1

## Objective

Define a generic report-only ASX comparator artifact schema for future deterministic
Appendix 5B, Appendix 4C, Appendix 4D, Appendix 4E, annual, half-year, and external
table comparator sidecar prototypes.

## Boundaries

- Do not implement parsers.
- Do not run extraction, Docling, OCR, comparator tools, Qdrant, news jobs, memory jobs,
  Cockpit chat, Home producers, runtime/model/GPU tests, parser routing, or canonical
  truth writes.
- Do not change gold labels, canonical scorecards, databases, Qdrant, news, memory,
  runtime config, source labels, or financial truth persistence.
- Do not import the schema into production extraction routing.
- Use only standard-library code in the schema module.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/asx_comparator_artifact_schema_v1_20260521.md`
- `python3 scripts/agent_job_registry.py list-active --repo-root /home/l4nd0/tenn-runtime`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/asx_comparator_artifact_schema_v1_20260521.md --repo-root /home/l4nd0/tenn-runtime`
- `uv run --with pytest python -m pytest financial-engine_v2/backend/tests/test_asx_comparator_artifact_schema.py -q`
- `uv run --with pytest python -m pytest financial-engine_v2/backend/tests/test_asx_document_type_fixture_contract.py financial-engine_v2/backend/tests/test_asx_document_type_classifier.py financial-engine_v2/backend/tests/test_asx_document_type_sidecar.py -q`
- `uv run --with pytest python -m pytest financial-engine_v2/backend/tests/test_asx_document_type_fixture_contract.py financial-engine_v2/backend/tests/test_asx_document_type_classifier.py financial-engine_v2/backend/tests/test_asx_document_type_sidecar.py financial-engine_v2/backend/tests/test_asx_comparator_artifact_schema.py -q`
- `python3 -m compileall financial-engine_v2/backend/app/services/asx_comparator_artifact_schema.py financial-engine_v2/backend/tests/test_asx_comparator_artifact_schema.py`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/asx_comparator_artifact_schema_v1_20260521.md`
