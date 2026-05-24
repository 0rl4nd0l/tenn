---
job_id: strategy_lab_quantdinger_manual_readonly_probe_v1_20260524
title: Strategy Lab QuantDinger manual read-only runtime probe
owner: Codex
lane: Reporting
primary_lane: Reporting
supporting_lanes:
  - Query Orchestration
  - Provenance
  - Evaluation
mutation_mode: safe_extension
approval_required: true
user_approval_captured: true
production_data_access: false
timeout_seconds: 10800
output_dir: reports/agent_jobs/strategy_lab_quantdinger_manual_readonly_probe_v1_20260524
allowed_files:
  - docs/agent_tasks/strategy_lab_quantdinger_manual_readonly_probe_v1_20260524.md
  - reports/agent_jobs/strategy_lab_quantdinger_manual_readonly_probe_v1_20260524/README.md
  - reports/agent_jobs/strategy_lab_quantdinger_manual_readonly_probe_v1_20260524/status.json
  - reports/agent_jobs/strategy_lab_quantdinger_manual_readonly_probe_v1_20260524/runtime_proof.json
  - reports/agent_jobs/strategy_lab_quantdinger_manual_readonly_probe_v1_20260524/no_mutation_attestation.json
  - reports/agent_jobs/strategy_lab_quantdinger_manual_readonly_probe_v1_20260524/validation.json
  - reports/agent_jobs/strategy_lab_quantdinger_manual_readonly_probe_v1_20260524/diff-check.json
---

# Strategy Lab QuantDinger Manual Read-Only Runtime Probe v1

## Objective

Run one bounded QuantDinger read-only runtime probe, or stop with a report-only
blocker if any safety precondition fails.

## Approval Captured

The user explicitly approved Docker startup, external clone or GHCR pull if
required, a short-lived sandbox R/B token, public/test BTC/USDT market-data
access, W/T denial checks, zero-order proof, token revocation, and full cleanup.

The user explicitly forbids broker credentials, live trading, paper orders, Tenn
store writes, canonical truth writes, and setting `current_sidecar_available=true`.

## Allowed Runtime Actions

Only inside the bounded probe:

- external clone or GHCR pull if required
- Docker startup on loopback only
- short-lived sandbox/read-browse R/B token only
- tiny public/test BTC/USDT market-data access
- health check
- market read
- read-only backtest if available
- regime detection if available
- W/T denial probes
- zero-order proof
- token revoke
- complete cleanup

## Forbidden

- No broker credentials.
- No live trading.
- No paper order placement.
- No market orders.
- No stored credentials.
- No persistent service install.
- No background scheduler.
- No Tenn DB, Qdrant, news, memory, or canonical truth writes.
- No Strategy Lab metadata/status mutation.
- No `current_sidecar_available=true`.
- No parser routing changes.
- No runtime/model/GPU config changes.
- No unrelated dirty task-card edits.
- No broad repo cleanup.

## Hard Stops

Stop before runtime if:

- task-card validation fails
- registry overlap or claim is unsafe
- target ports cannot be isolated to loopback
- any broker/live/paper/order capability cannot be disabled
- any token would persist or leak
- any Tenn store/canonical truth write would occur
- Docker cleanup cannot be proven
- HIGH repo overlap appears
- validation reveals unsafe or uncontainable behavior

## Required Proof

Capture exact commands, ports before/during/after, containers/images/volumes/networks
created, health response, token type/scope and revoke proof without secrets,
market-read proof, W/T denial proof, zero-order proof, and cleanup proof.

## Deliverables

- `reports/agent_jobs/strategy_lab_quantdinger_manual_readonly_probe_v1_20260524/README.md`
- `reports/agent_jobs/strategy_lab_quantdinger_manual_readonly_probe_v1_20260524/status.json`
- `reports/agent_jobs/strategy_lab_quantdinger_manual_readonly_probe_v1_20260524/runtime_proof.json`
- `reports/agent_jobs/strategy_lab_quantdinger_manual_readonly_probe_v1_20260524/no_mutation_attestation.json`
- `reports/agent_jobs/strategy_lab_quantdinger_manual_readonly_probe_v1_20260524/validation.json`
- `reports/agent_jobs/strategy_lab_quantdinger_manual_readonly_probe_v1_20260524/diff-check.json`
