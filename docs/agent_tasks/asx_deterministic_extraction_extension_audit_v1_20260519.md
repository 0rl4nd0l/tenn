---
job_id: asx_deterministic_extraction_extension_audit_v1_20260519
lane: Financial Truth
owner: Codex
mutation_mode: audit_only
production_data_access: false
approval_required: false
allow_audit_code_changes: true
output_dir: reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519
allowed_files:
  - docs/agent_tasks/asx_deterministic_extraction_extension_audit_v1_20260519.md
  - reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/
  - reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/README.md
  - reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/extension_point_inventory.json
  - reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/document_type_classifier_plan.json
  - reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/deterministic_parser_plan.md
  - reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/comparator_artifact_plan.md
  - reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/no_regression_gate_map.json
  - reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/DATA_MISSING.md
  - reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/status.json
  - reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/diff-check.json
timeout_seconds: 7200
---

# Task

Audit how Tenn can safely extend extraction beyond the current strict Docling baseline using ASX-aware deterministic document-type classification, Appendix 5B/4C/4D/4E parsers, annual/half-year statement-table selectors, and read-only comparator artifacts.

# Mode

AUDIT ONLY. Do not implement extraction changes. Do not change parser routing, prompts, gold labels, canonical writes, runtime, DBs, Qdrant, memory, news, Cockpit, source labels, or production truth semantics.

# Allowed Work

- Inspect extraction, evaluation, architecture, gold, and report artifacts read-only.
- Write report artifacts only under `reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/`.
- Run task-card validation, registry checks, JSON validation, `git diff --check`, and task-card `check-diff`.

# Required Report

Write `reports/agent_jobs/asx_deterministic_extraction_extension_audit_v1_20260519/README.md` with:

- executive verdict;
- confirmed facts;
- inferred facts;
- speculative claims;
- `DATA_MISSING`;
- extension point inventory;
- ASX document-type classifier plan;
- deterministic parser plan;
- comparator artifact plan;
- no-regression and promotion gates;
- safe roadmap;
- do-not-do list;
- validation commands run;
- final git status;
- registry release status;
- project memory save recommendation.

# Hard Boundaries

Do not run extraction jobs, live Docling extraction, OCR/comparator tools, runtime/model/GPU changes, canonical writes, database writes, Qdrant writes, memory changes, news changes, Cockpit changes, source changes, commits, stashes, cleans, or broad production extraction accuracy claims.
