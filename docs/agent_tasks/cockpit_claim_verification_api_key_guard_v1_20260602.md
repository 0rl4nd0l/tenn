---
job_id: cockpit_claim_verification_api_key_guard_v1_20260602
lane: Query Orchestration
owner: Codex
allowed_files:
  - docs/agent_tasks/cockpit_claim_verification_api_key_guard_v1_20260602.md
  - financial-engine_v2/backend/app/routes/cockpit_claims.py
  - financial-engine_v2/backend/tests/test_claim_verification.py
  - financial-engine_v2/backend/tests/test_local_api_key.py
  - reports/agent_jobs/cockpit_claim_verification_api_key_guard_v1_20260602/README.md
  - reports/agent_jobs/cockpit_claim_verification_api_key_guard_v1_20260602/status.json
  - reports/agent_jobs/cockpit_claim_verification_api_key_guard_v1_20260602/validation.json
  - reports/agent_jobs/cockpit_claim_verification_api_key_guard_v1_20260602/diff-check.json
approval_required: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/cockpit_claim_verification_api_key_guard_v1_20260602
mutation_mode: safe_extension
production_data_access: false
---

# Cockpit Claim Verification API Key Guard

## Scope

Fix GitHub issue #224 by requiring the configured local API key on the backend Cockpit claim verification route.

## Target Layer

Backend Query Orchestration route boundary for Cockpit claim verification. The route remains a backend API surface; Cockpit UI/BFF clients remain responsible for forwarding configured `X-API-Key` headers.

## Contract Rules

- Backend remains the authority for protected API route access control.
- Cockpit remains a client/orchestration layer and must not bypass backend route guards.
- Claim verification semantics must not change for authenticated callers.
- No data store, Qdrant, memory, extraction, parser, model, runtime, or financial-truth surfaces may change.
- No fallback or alternate unauthenticated path may be introduced.

## Acceptance Criteria

- `POST /api/cockpit/claims/verify` rejects missing or wrong API keys when `local_api_key` is configured.
- The same endpoint still succeeds with a matching `X-API-Key`.
- The endpoint keeps returning `400` for empty `assistant_text` after auth succeeds.
- Route-registration coverage proves the endpoint has the canonical `require_api_key` dependency.
- Existing claim verification verdict behavior remains unchanged.
