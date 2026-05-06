---
job_id: verification-source-page-viewer-import-valid-v1
lane: Reporting
owner: Codex
mutation_mode: safe_extension
production_data_access: false
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
stale_after_seconds: 7200
output_dir: reports/agent_jobs/verification-source-page-viewer-import-valid-v1
allowed_files:
  - docs/agent_tasks/verification-source-page-viewer-import-valid-v1.md
  - cockpit-ui/components/cockpit/verification/tabs/metric-coverage-tab-panel.tsx
  - cockpit-ui/components/cockpit/verification/tabs/metric-coverage-tab-panel.test.tsx
  - cockpit-ui/components/cockpit/verification/types.ts
  - cockpit-ui/components/cockpit/verification/verification-screen.tsx
  - financial-engine_v2/backend/app/main.py
  - financial-engine_v2/backend/app/services/confirmed_metric_coverage_review.py
  - financial-engine_v2/backend/tests/test_confirmed_metric_coverage_api.py
  - financial-engine_v2/backend/tests/test_confirmed_metric_coverage_review.py
  - financial-engine_v2/backend/app/models/companies.py
  - .gitignore
  - reports/agent_jobs/verification-source-page-viewer-import-valid-v1/validation.json
  - reports/agent_jobs/verification-source-page-viewer-import-valid-v1/status.json
  - reports/agent_jobs/verification-source-page-viewer-import-valid-v1/diff-check.json
  - reports/agent_jobs/verification-source-page-viewer-import-valid-v1/no-mutation-proof.txt
---

# Verification Source Page Viewer Import-Valid Integration

## Task

Replay or integrate the verified Verification Metric Coverage clickthrough and source-page viewer work onto an import-valid backend base, then validate it without process-local backend import stubs.

## Boundaries

Do not run extraction, start `:8002`, use GPU, mutate labels, edit canonical gold, write financial DB rows, write Qdrant, modify extraction logic, modify prompts, modify parser routing, loosen validation, promote candidate metrics, touch unrelated Marketplace/chat/home work, or edit `financial-engine_v2/backend/app/routes/cockpit_api.py`.

## Required Validation

- Validate this task card before mutation beyond the card itself.
- List active registry jobs and claim this card if supported.
- Prove the base is import-valid with tracked `financial-engine_v2/backend/app/models/companies.py`.
- Run backend import preflight without import stubs.
- Run targeted backend confirmed metric coverage/source-route tests.
- Run targeted Metric Coverage frontend tests and targeted lint/type checks.
- Run browser smoke with real backend and real UI where possible.
- Prove no extraction, runtime `:8002`, DB financial, label, or Qdrant mutation.

## Final Report Requirements

Report the base HEAD, integrated commit(s), import-validity result, files changed, exact tests and results, browser smoke result, no-mutation proof, limitations, and one recommended next action.
