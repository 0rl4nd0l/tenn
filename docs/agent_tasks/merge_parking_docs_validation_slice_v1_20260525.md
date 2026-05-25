---
job_id: merge_parking_docs_validation_slice_v1_20260525
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/merge_parking_docs_validation_slice_v1_20260525.md
  - docs/agent_registry/merge_parking/README.md
  - docs/agent_registry/merge_parking/REGISTRY.md
  - docs/agent_registry/merge_parking/_entry_template.md
  - docs/agent_registry/merge_parking/merge_parking_entry_schema_v1.json
  - docs/agent_registry/merge_parking/registry_schema_v1.json
  - scripts/merge_parking_registry.py
  - scripts/test_merge_parking_registry.py
  - reports/agent_jobs/merge_parking_docs_validation_slice_v1_20260525/README.md
  - reports/agent_jobs/merge_parking_docs_validation_slice_v1_20260525/status.json
  - reports/agent_jobs/merge_parking_docs_validation_slice_v1_20260525/validation.json
  - reports/agent_jobs/merge_parking_docs_validation_slice_v1_20260525/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/merge_parking_docs_validation_slice_v1_20260525
mutation_mode: safe_extension
production_data_access: false
---

# Task

Implement GitHub #68: merge parking docs and validation slice v1.

# Scope

Add or validate repo-native merge parking documentation, entry/index templates,
schemas, and changed-file-scoped validation for merge-parking artifacts only.

# Hard Boundaries

- Do not implement auto-merge, auto-cherry-pick, auto-rebase, reset, stash,
  branch deletion, cleanup automation, or Git-ref claims.
- Do not implement broad CI gates.
- Do not touch product, backend, frontend, runtime, financial-truth, memory,
  Qdrant, DB, news, parser-routing, extraction, Docker, cron, systemd, model, or
  GPU files.
- Parking must remain review-only and must not imply merge approval.
- Mutate only this task card, listed merge parking docs/schemas/helper/test
  files, and listed report artifacts.

# Required Outputs

- Merge parking states and freeze/review rules documented.
- Entry/index templates.
- Changed-file-scoped validation helper.
- Focused tests covering valid entry, invalid status, missing required fields,
  review-required metadata, and changed-file scope.
- Report artifacts under
  `reports/agent_jobs/merge_parking_docs_validation_slice_v1_20260525/`.

# Validation

Run and report task-card validate, registry list/check-overlap/claim/release,
JSON checks, merge parking validation helper checks, focused tests, ruff where
available, `git diff --check`, and task-card check-diff.
