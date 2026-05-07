---
job_id: source-page-viewer-import-repair-integration-v1
lane: Reporting
owner: Codex
mutation_mode: safe_extension
production_data_access: false
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
stale_after_seconds: 7200
output_dir: reports/agent_jobs/source-page-viewer-import-repair-integration-v1
allowed_files:
  - docs/agent_tasks/source-page-viewer-import-repair-integration-v1.md
  - .gitignore
  - financial-engine_v2/backend/app/models/companies.py
  - financial-engine_v2/backend/app/models/__init__.py
  - financial-engine_v2/backend/app/main.py
  - financial-engine_v2/backend/app/services/confirmed_metric_coverage_review.py
  - financial-engine_v2/backend/tests/test_confirmed_metric_coverage_api.py
  - financial-engine_v2/backend/tests/test_confirmed_metric_coverage_review.py
  - financial-engine_v2/backend/tests/test_extraction_gold_eval_scorecard.py
  - cockpit-ui/components/cockpit/verification/**
  - cockpit-ui/app/verification/**
  - reports/agent_jobs/source-page-viewer-import-repair-integration-v1/**
---

# Source Page Viewer Import Repair Integration v1

## Task

Integrate the backend companies model import repair with the validated Metric Coverage source-page viewer workflow.

## Lane Classification

- Primary lane: Reporting
- Supporting lanes: Evaluation, Provenance
- Financial Truth: read-only

## Execution Mode

- Audit Mode first
- Safe Extension Mode only if collision risk is LOW or acceptable MEDIUM
- Safe Validation Mode for targeted tests and default-service smoke
- Blocked Mode if branch/worktree state is unsafe

## Primary Goal

Ensure the target/default source-page viewer branch includes backend import repair commit `1976399726afd7adfb64e714c2d3c73f6103cd72` and validate that clean backend import and Metric Coverage source-page viewer work together.

## Strict Boundaries

Do not:

- run extraction
- start `:8002`
- use GPU
- mutate labels
- edit canonical gold
- write financial DB rows
- write Qdrant
- modify extraction logic
- modify prompts
- modify parser routing
- loosen validation
- touch unrelated Marketplace/chat/home dirty work
- touch `financial-engine_v2/backend/app/routes/cockpit_api.py`
- expose arbitrary filesystem paths

## Required Checks

- Validate this task card before mutation beyond the card itself.
- List active registry jobs and claim this card if supported.
- Confirm the source-page viewer implementation is present on the target branch.
- Confirm whether the backend import repair is already present.
- If absent, cherry-pick `1976399726afd7adfb64e714c2d3c73f6103cd72` without resolving unsafe conflicts.
- Run backend import preflight without process-local stubs.
- Run targeted confirmed metric coverage backend tests.
- Run targeted Metric Coverage frontend tests and focused lint/type checks for touched UI surfaces.
- Run `git diff --check` and task-card `check-diff` if supported.
- If safe, run default service smoke against backend `:8000` and Cockpit `:8081` without starting extraction runtime `:8002`.

## Final Report Requirements

Report lane, mode, collision, branch, HEAD before/after, task card, registry, dirty files, integration result, exact validation evidence, service smoke evidence or DATA_MISSING, files changed, forbidden files touched, final verdict, and one recommended next action.
