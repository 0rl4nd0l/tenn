---
job_id: marketplace_capture_single_use_token_v1_20260602
lane: Reporting
owner: Codex
allowed_files:
  - docs/agent_tasks/marketplace_capture_single_use_token_v1_20260602.md
  - cockpit-ui/lib/marketplace-capture-tokens.ts
  - cockpit-ui/lib/marketplace-capture-tokens.test.ts
  - cockpit-ui/app/api/cockpit/commentary/marketplace-capture/submit/route.ts
  - reports/agent_jobs/marketplace_capture_single_use_token_v1_20260602/README.md
  - reports/agent_jobs/marketplace_capture_single_use_token_v1_20260602/status.json
  - reports/agent_jobs/marketplace_capture_single_use_token_v1_20260602/validation.json
  - reports/agent_jobs/marketplace_capture_single_use_token_v1_20260602/diff-check.json
approval_required: true
timeout_seconds: 3600
output_dir: reports/agent_jobs/marketplace_capture_single_use_token_v1_20260602
mutation_mode: safe_extension
production_data_access: false
---

# Marketplace Capture Single-Use Token

## Scope

Harden the Cockpit Marketplace capture helper token path so a valid helper token is consumed on the first submit attempt and cannot replay the ingest relay during the token TTL.

## Issue

GitHub issue #217 reports that `getMarketplaceCaptureToken()` currently reads a valid token without deleting it, which allows repeated submits until expiry.

## Target Layer

Cockpit Reporting BFF/control-token surface only. The backend ingest endpoint remains authoritative for snapshot persistence.

## Contract Rules

- Do not alter canonical financial facts or backend source-of-truth persistence.
- Do not weaken missing-token or expired-token handling.
- Do not introduce an alternate backend ingest path.
- Preserve issue #52 behavior for missing helper tokens.

## Acceptance Criteria

- First submit with a valid Marketplace capture token preserves existing relay behavior.
- Second submit with the same token returns the expired-helper 410 path.
- Replay does not call backend ingest.
- Backend relay failure still consumes the token so retries require a fresh helper.
- Focused tests cover token-store single-use behavior and submit-route replay behavior.
