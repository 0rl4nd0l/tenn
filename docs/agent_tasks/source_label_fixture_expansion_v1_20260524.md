---
job_id: source_label_fixture_expansion_v1_20260524
lane: Provenance
owner: Codex
allowed_files:
  - docs/agent_tasks/source_label_fixture_expansion_v1_20260524.md
  - reports/agent_jobs/source_label_fixture_expansion_v1_20260524/README.md
  - reports/agent_jobs/source_label_fixture_expansion_v1_20260524/status.json
  - reports/agent_jobs/source_label_fixture_expansion_v1_20260524/validation.json
  - reports/agent_jobs/source_label_fixture_expansion_v1_20260524/fixture_coverage_map.json
  - reports/agent_jobs/source_label_fixture_expansion_v1_20260524/gap_register.json
  - reports/agent_jobs/source_label_fixture_expansion_v1_20260524/diff-check.json
approval_required: false
allow_audit_code_changes: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/source_label_fixture_expansion_v1_20260524
mutation_mode: audit_only
production_data_access: false
---

# Task

Close GitHub #56 by running the issue-exact source-label fixture expansion
audit-first task. Locate current positive and negative source-label fixture
coverage, separate covered cases from gaps, and recommend the next bounded
fixture implementation if exact test files are safe in a later task.

# Scope

Write only this task card and the listed report artifacts. Do not change
source-label semantics, fixtures, tests, backend/frontend product code, runtime
behavior, or data stores in this audit-only pass.

# Hard Boundaries

- Do not relax source labels, change source-label semantics, alter canonical
  truth, change financial metrics, mutate production data, or change
  DB/Qdrant/news/memory stores.
- Do not edit contested Query Orchestration, Provenance, or Cockpit product
  files in this pass.
- Preserve DATA_MISSING / missing-required-evidence semantics.

# Required Outputs

- `reports/agent_jobs/source_label_fixture_expansion_v1_20260524/README.md`
- `status.json`
- `fixture_coverage_map.json`
- `gap_register.json`
- Recommended child implementation if exact test files are safe.

# Validation

Run and report task-card validate, registry list-active, check-overlap, claim,
JSON validation, targeted existing fixture/test checks when safe, `git diff
--check`, task-card check-diff, registry release, and final registry
list-active.
