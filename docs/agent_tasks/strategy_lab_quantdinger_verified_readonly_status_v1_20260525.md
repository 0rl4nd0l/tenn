---
job_id: strategy_lab_quantdinger_verified_readonly_status_v1_20260525
title: Strategy Lab QuantDinger verified read-only status wording
owner: Codex
lane: Reporting
primary_lane: Reporting
supporting_lanes:
  - Provenance
  - Query Orchestration
mutation_mode: safe_extension
approval_required: true
user_approval_captured: true
production_data_access: false
timeout_seconds: 7200
output_dir: reports/agent_jobs/strategy_lab_quantdinger_verified_readonly_status_v1_20260525
allowed_files:
  - docs/agent_tasks/strategy_lab_quantdinger_verified_readonly_status_v1_20260525.md
  - reports/agent_jobs/strategy_lab_quantdinger_verified_readonly_status_v1_20260525/README.md
  - reports/agent_jobs/strategy_lab_quantdinger_verified_readonly_status_v1_20260525/status.json
  - reports/agent_jobs/strategy_lab_quantdinger_verified_readonly_status_v1_20260525/validation.json
  - reports/agent_jobs/strategy_lab_quantdinger_verified_readonly_status_v1_20260525/diff-check.json
  - cockpit-ui/lib/strategy-lab-status.ts
  - cockpit-ui/lib/strategy-lab-status-server.ts
  - cockpit-ui/lib/strategy-lab-status.test.ts
  - cockpit-ui/lib/strategy-lab-artifacts.ts
  - cockpit-ui/lib/strategy-lab-artifacts-server.ts
  - cockpit-ui/lib/strategy-lab-artifacts.test.ts
  - cockpit-ui/components/cockpit/home/cards/strategy-lab-status-card.tsx
  - cockpit-ui/components/cockpit/home/cards/strategy-lab-status-card.test.tsx
  - cockpit-ui/components/cockpit/home/cards/strategy-lab-artifacts-review-card.tsx
  - cockpit-ui/components/cockpit/home/cards/strategy-lab-artifacts-review-card.test.tsx
---

# Strategy Lab QuantDinger Verified Read-Only Status v1

## Objective

Update the Strategy Lab / QuantDinger UI, status contract, artifact review
metadata, and focused tests so Cockpit can honestly show the clean re-probe
evidence as verified read-only sandbox proof while keeping the sidecar offline,
pending review, non-executing, and non-canonical.

Use evidence only from:

- `reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/`

## Required Wording Boundary

The UI/status wording may say:

- `Verified read-only sandbox proof available`
- historical smoke proof exists
- clean re-probe evidence artifacts are available
- zero-order, revoke, and cleanup proof exists
- results remain `PENDING_REVIEW`
- `current_sidecar_available=false`

The UI/status wording must not imply:

- the QuantDinger sidecar is online now
- the sidecar is persistent or integrated with Cockpit transport
- Tenn can place live trades, paper orders, or broker orders
- sidecar output is Tenn canonical financial truth
- sidecar output writes Tenn DB, Qdrant, news, memory, or artifact stores

## Allowed Scope

- Strategy Lab status/artifact display files under `cockpit-ui/`.
- Focused Strategy Lab tests.
- This task card and report artifacts.

## Forbidden

- No runtime startup.
- No Docker.
- No token issuance.
- No broker, live, or paper trading.
- No `current_sidecar_available=true`.
- No real transport integration.
- No Tenn DB, Qdrant, news, memory, or canonical financial truth writes.
- No parser, routing, runtime, or model config edits.
- No production data access.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/strategy_lab_quantdinger_verified_readonly_status_v1_20260525.md`
- `python3 scripts/agent_job_registry.py list-active`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/strategy_lab_quantdinger_verified_readonly_status_v1_20260525.md --repo-root .`
- Focused Strategy Lab Vitest.
- Cockpit UI TypeScript and targeted lint if relevant.
- JSON parse for status/report artifacts and clean re-probe evidence artifacts.
- `git diff --check`.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/strategy_lab_quantdinger_verified_readonly_status_v1_20260525.md --repo-root .`

## Done Criteria

The Strategy Lab UI/status/artifact wording can show verified read-only sandbox
proof availability while still proving `current_sidecar_available=false`, no
trading, no paper orders, no store writes, no real transport integration, and
no canonical financial truth.
