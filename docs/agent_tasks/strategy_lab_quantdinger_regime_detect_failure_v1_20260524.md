---
job_id: strategy_lab_quantdinger_regime_detect_failure_v1_20260524
title: Strategy Lab QuantDinger regime detect failure investigation
owner: Codex
lane: Reporting
primary_lane: Reporting
supporting_lanes:
  - Evaluation
  - Query Orchestration
mutation_mode: audit_only
allow_audit_code_changes: true
approval_required: true
user_approval_captured: true
production_data_access: false
timeout_seconds: 10800
output_dir: reports/agent_jobs/strategy_lab_quantdinger_regime_detect_failure_v1_20260524
allowed_files:
  - docs/agent_tasks/strategy_lab_quantdinger_regime_detect_failure_v1_20260524.md
  - reports/agent_jobs/strategy_lab_quantdinger_regime_detect_failure_v1_20260524/README.md
  - reports/agent_jobs/strategy_lab_quantdinger_regime_detect_failure_v1_20260524/status.json
  - reports/agent_jobs/strategy_lab_quantdinger_regime_detect_failure_v1_20260524/evidence.json
  - reports/agent_jobs/strategy_lab_quantdinger_regime_detect_failure_v1_20260524/validation.json
  - reports/agent_jobs/strategy_lab_quantdinger_regime_detect_failure_v1_20260524/diff-check.json
---

# Strategy Lab QuantDinger Regime Detect Failure Investigation v1

## Objective

Investigate why the manual read-only QuantDinger probe returned HTTP 400 from
`POST /api/agent/v1/experiments/regime/detect` with message
`single positional indexer is out-of-bounds`.

Classify the failure as one or more of:

- bad request shape
- insufficient market rows
- endpoint bug
- fixture/data-window issue
- expected limitation

## Input Evidence

Use the manual probe report at
`reports/agent_jobs/strategy_lab_quantdinger_manual_readonly_probe_v1_20260524/`.

## Allowed Actions

- Read Tenn task cards, reports, Strategy Lab docs, and tests.
- Inspect external QuantDinger source/readme material as evidence.
- Write only this task card and the report artifacts listed in `allowed_files`.
- Run validation commands that are read-only against Tenn data stores.
- If a runtime re-smoke is required, it must be loopback-only, read-only,
  no-order, zero-store-write, token-redacted, and include full cleanup proof.

## Forbidden

- No live trading.
- No paper order placement.
- No broker credentials.
- No token storage.
- No Tenn DB, Qdrant, news, memory, or canonical truth writes.
- No Strategy Lab UI/status mutation.
- No `current_sidecar_available=true`.
- No transport integration.
- No product-code edits unless a later approval explicitly widens this card.

## Hard Stops

Stop before implementation if:

- task-card validation fails
- registry overlap is unsafe
- unresolved HIGH collision risk touches contested surfaces
- diagnosis would require live trading, paper orders, credentials, or store writes
- runtime re-smoke cannot remain loopback-only and fully cleaned up

## Required Output

The final report must include:

- root cause
- exact reproduction/request payload, or `DATA_MISSING` with the missing evidence
- whether a narrow fix is safe
- tests and validation
- whether a clean re-probe is now justified
- save recommendation
