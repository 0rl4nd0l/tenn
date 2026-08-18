---
job_id: direct_startup_runtime_diagnostics_current_base_v3_20260627
lane: Reporting
supporting_lanes:
  - Evaluation
  - Runtime
  - Repo Hygiene
owner: Codex
allowed_files:
  - docs/agent_tasks/direct_startup_runtime_diagnostics_current_base_v3_20260627.md
  - financial-engine_v2/backend/app/core/startup_diagnostics.py
  - financial-engine_v2/backend/app/main.py
  - financial-engine_v2/backend/tests/test_startup_diagnostics.py
  - financial-engine_v2/scripts/run_local_backend.sh
  - scripts/test_run_local_backend_script.py
  - reports/agent_jobs/direct_startup_runtime_diagnostics_current_base_v3_20260627/README.md
  - reports/agent_jobs/direct_startup_runtime_diagnostics_current_base_v3_20260627/STATE.md
  - reports/agent_jobs/direct_startup_runtime_diagnostics_current_base_v3_20260627/VALIDATION.md
  - reports/agent_jobs/direct_startup_runtime_diagnostics_current_base_v3_20260627/REVIEW.md
  - reports/agent_jobs/direct_startup_runtime_diagnostics_current_base_v3_20260627/PR_BODY.md
  - reports/agent_jobs/direct_startup_runtime_diagnostics_current_base_v3_20260627/status.json
  - reports/agent_jobs/direct_startup_runtime_diagnostics_current_base_v3_20260627/validation.json
  - reports/agent_jobs/direct_startup_runtime_diagnostics_current_base_v3_20260627/diff-check.json
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/direct_startup_runtime_diagnostics_current_base_v3_20260627
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
docs_impact: NONE
docs_checked:
  - AGENTS.md
  - docs/README.md
  - docs/dev_flow/REPO_PATH_OWNERSHIP_AND_WORK_PRESERVATION.md
  - docs/entrypoints.md
docs_changed: []
docs_followup: NONE
reason: "Issue #280 asks for startup diagnostics only; no service start, runtime mutation, or default behavior change."
task_tier: medium
recommended_model: "standard coding model"
actual_model: "Codex GPT-5"
why_this_model: "Focused backend startup diagnostics/reporting change with unit tests."
worker_model_allowed: false
worker_decision_limit: "No workers used; scope is narrow and source-local."
escalation_needed: false
related_issue: 280
---

# Direct Startup Runtime Diagnostics

## Objective

Close issue #280 by making direct or unknown backend startup clearly report
effective runtime mode, database URL class, and feature flags, while preserving
the canonical isolated `run_local_backend.sh` path.

## Scope

- Port useful prior work from stale
  `/home/l4nd0/tenn-issue280-direct-startup-diagnostics-v1-20260626` onto
  current canonical.
- Add pure startup diagnostics helpers for DB URL class, entrypoint label,
  runtime feature summary, and direct-startup warning decisions.
- Log those diagnostics in `main.py` startup config output.
- Mark `run_local_backend.sh` with `TENN_BACKEND_ENTRYPOINT=run_local_backend`
  so canonical local startup is distinguishable from direct/unknown uvicorn.
- Add focused helper and script-marker tests.

## Hard Stops

- Do not start services.
- Do not change default runtime feature flags.
- Do not mutate DB, Redis, Qdrant, news, memory, source PDFs, extraction
  prompts, gold labels, runtime/model/GPU/service config, or production data.
- Do not add fail-fast behavior in this slice.
- Do not change Cockpit/frontend behavior.

## Validation

- Task-card validate.
- Registry overlap check and claim.
- Focused backend tests for startup diagnostics helper.
- Focused script test for `run_local_backend.sh` marker.
- Targeted Ruff check when available through `uv`.
- `python3 -m py_compile` on touched Python files.
- `bash -n financial-engine_v2/scripts/run_local_backend.sh`.
- `git diff --check`.
- Task-card `check-diff` and `check-report-artifacts`.
