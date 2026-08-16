---
job_id: verification_source_pdf_bff_auth_parity_v1_20260601
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/verification_source_pdf_bff_auth_parity_v1_20260601.md
  - reports/agent_jobs/verification_source_pdf_bff_auth_parity_v1_20260601/
  - reports/agent_jobs/verification_source_pdf_bff_auth_parity_v1_20260601/README.md
  - reports/agent_jobs/verification_source_pdf_bff_auth_parity_v1_20260601/status.json
  - reports/agent_jobs/verification_source_pdf_bff_auth_parity_v1_20260601/validation.json
  - reports/agent_jobs/verification_source_pdf_bff_auth_parity_v1_20260601/diff-check.json
  - cockpit-ui/app/api/extraction-eval/confirmed-metric-coverage/source/route.ts
  - cockpit-ui/components/cockpit/verification/tabs/metric-coverage-tab-panel.tsx
  - cockpit-ui/components/cockpit/verification/tabs/metric-coverage-tab-panel.test.tsx
  - cockpit-ui/lib/verification-source-route.test.ts
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/verification_source_pdf_bff_auth_parity_v1_20260601
mutation_mode: safe_extension
production_data_access: false
---

# Verification Source PDF BFF Auth Parity V1

Resolve GitHub issue #155 by routing Verification source-PDF opening through an authenticated Cockpit BFF route instead of relying on a browser navigation rewrite to the protected backend route.

## Scope

- Add a Next BFF route for `GET /api/extraction-eval/confirmed-metric-coverage/source`.
- Forward the configured Cockpit API key server-side to the existing backend allowlisted source route.
- Preserve backend status, PDF content type, and content disposition.
- Show `DATA_MISSING` in the UI when no API key is available for the authenticated source-open path.
- Add focused route and UI tests for authenticated forwarding and no-key failure state.

## Forbidden

- No production DB/Qdrant/news/memory writes.
- No canonical financial truth, parser routing, extraction prompt, or gold-label changes.
- No source PDF or raw filing bundle changes.
- No backend source-route allowlist weakening.
- No disabling or bypassing `require_api_key()`.
- No unrelated dirty work.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/verification_source_pdf_bff_auth_parity_v1_20260601.md`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/verification_source_pdf_bff_auth_parity_v1_20260601.md`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/verification_source_pdf_bff_auth_parity_v1_20260601.md`
- focused Verification tab and BFF route tests
- targeted ESLint for changed files
- TypeScript
- Next build if practical
- authenticated local smoke fetch without printing secrets
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/verification_source_pdf_bff_auth_parity_v1_20260601.md`
