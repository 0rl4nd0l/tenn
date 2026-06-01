---
job_id: root_owned_python_cache_validation_blocker_v1
lane: Evaluation
requested_primary_lane: Repo Hygiene
supporting_lanes:
  - Evaluation
  - Runtime
owner: Codex
mutation_mode: audit_only
allow_audit_code_changes: true
production_data_access: false
approval_required: false
timeout_seconds: 3600
output_dir: reports/agent_jobs/root_owned_python_cache_validation_blocker_v1
allowed_files:
  - docs/agent_tasks/root_owned_python_cache_validation_blocker_v1.md
  - reports/agent_jobs/root_owned_python_cache_validation_blocker_v1/README.md
  - reports/agent_jobs/root_owned_python_cache_validation_blocker_v1/cache_inventory.json
  - reports/agent_jobs/root_owned_python_cache_validation_blocker_v1/cleanup_decision.md
  - reports/agent_jobs/root_owned_python_cache_validation_blocker_v1/status.json
  - reports/agent_jobs/root_owned_python_cache_validation_blocker_v1/validation.json
  - reports/agent_jobs/root_owned_python_cache_validation_blocker_v1/diff-check.json
inspect_only_surfaces:
  - /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/**/__pycache__/
  - .gitignore
  - reports/agent_jobs/asx_document_type_sidecar_artifact_v1_20260520/README.md
  - reports/agent_jobs/asx_document_type_pure_classifier_v1_20260520/README.md
---

# Task

Create a report-only closeout artifact for GitHub issue #140 that inventories root-owned ignored Python cache directories and records why cleanup is deferred while another active job owns the shared checkout.

# GitHub tracking

- Issue: https://github.com/0rl4nd0l/tenn/issues/140
- PR link policy: use `Refs #140`; this is blocker evidence, not cleanup completion.

# Target layer and contract

- Target layer: repo hygiene / generated local validation state.
- Relevant contract rules: no backend/product authority changes; no financial truth mutation; no runtime/model/GPU/service config mutation; no broad destructive cleanup.
- What must not change: tracked product code, DB, Qdrant, news, memory, canonical financial truth, parser routing, extraction prompts, gold labels, runtime services, or unrelated dirty work.
- Safety basis: writes are limited to this task card and report artifacts. Root-owned generated cache directories are read-only inventoried and not removed or ownership-mutated in this job.
- GPU process check required: no.

# Required analysis

1. Inventory root-owned ignored Python `__pycache__` directories in the shared checkout.
2. Record owner, group, mode, and path.
3. Re-check duplicate PR coverage.
4. Re-check active registry jobs and collision risk.
5. Decide whether cleanup can run now.
6. Record cleanup/compile validation blockers as `DATA_MISSING`.

# Hard stops

Stop and report only if:
- a duplicate PR already covers #140
- tracked files would be removed or modified by cleanup
- active same-checkout ownership creates collision risk
- broad destructive cleanup would be required
- elevated cleanup would be required outside the task contract

# Validation

Run:
- `gh issue view 140 --repo 0rl4nd0l/tenn --json number,title,state,body,labels,url,comments`
- duplicate PR search for #140/root-owned cache terms
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/root_owned_python_cache_validation_blocker_v1.md`
- `python3 scripts/agent_job_registry.py list-active --read-only`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/root_owned_python_cache_validation_blocker_v1.md`
- root-owned cache `find` inventory against the shared checkout
- JSON parse checks
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/root_owned_python_cache_validation_blocker_v1.md`
- `git diff --check`
- `git diff --cached --check`

# Definition of done

- The current root-owned cache inventory is preserved in a report bundle.
- Cleanup is either completed or explicitly deferred with current evidence.
- No generated cache directory is removed, chowned, or quarantined by this report-only job.
- No tracked product/runtime/data surface is changed.
