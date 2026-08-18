---
job_id: strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525
title: Strategy Lab QuantDinger clean re-probe evidence persistence
owner: Codex
lane: Evaluation
primary_lane: Evaluation
supporting_lanes:
  - Reporting
  - Provenance
mutation_mode: safe_extension
approval_required: true
user_approval_captured: true
production_data_access: false
timeout_seconds: 10800
output_dir: reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525
allowed_files:
  - docs/agent_tasks/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525.md
  - reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/README.md
  - reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/cleanup_proof.json
  - reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/diff-check.json
  - reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/no_mutation_attestation.json
  - reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/payloads/agent_health_response.json
  - reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/payloads/attempt1_list_payload_rejected/agent_health_response.json
  - reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/payloads/attempt1_list_payload_rejected/health_response.json
  - reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/payloads/attempt1_list_payload_rejected/markets_response.json
  - reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/payloads/attempt1_list_payload_rejected/post_revoke_whoami_response.json
  - reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/payloads/attempt1_list_payload_rejected/revoke_response.json
  - reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/payloads/attempt1_list_payload_rejected/symbols_response.json
  - reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/payloads/attempt1_list_payload_rejected/token_issue_request.json
  - reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/payloads/attempt1_list_payload_rejected/token_issue_response_sanitized.json
  - reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/payloads/attempt1_list_payload_rejected/whoami_response.json
  - reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/payloads/backtest_final_response.json
  - reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/payloads/backtest_request.json
  - reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/payloads/backtest_submit_response.json
  - reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/payloads/denial_responses.json
  - reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/payloads/health_response.json
  - reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/payloads/klines_response.json
  - reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/payloads/markets_response.json
  - reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/payloads/paper_orders_after_response.json
  - reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/payloads/paper_orders_before_response.json
  - reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/payloads/post_revoke_whoami_response.json
  - reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/payloads/regime_candle_count_probe.json
  - reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/payloads/regime_request.json
  - reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/payloads/regime_response.json
  - reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/payloads/revoke_response.json
  - reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/payloads/symbols_response.json
  - reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/payloads/token_issue_request.json
  - reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/payloads/token_issue_response_sanitized.json
  - reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/payloads/whoami_response.json
  - reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/payloads/zero_order_proof.json
  - reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/runtime_proof.json
  - reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/status.json
  - reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/validation.json
  - reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/validation_pre_cleanup.json
---

# Strategy Lab QuantDinger Clean Re-Probe Evidence Persistence v1

## Objective

Run one bounded loopback-only QuantDinger read-only re-probe using the patched
upstream regime segment guard and persist exact evidence for the runtime
boundary.

The target proof is `VERIFIED_READ_ONLY_SIDECAR_SANDBOX_VIABILITY` if all
required probes pass. This proof must not promote current Strategy Lab sidecar
availability.

## Required Success Criteria

- Regime detect passes cleanly.
- Exact request payloads are persisted.
- Candle counts are persisted.
- Response bodies are persisted.
- Zero orders are proven before and after.
- Token revocation is proven.
- Runtime cleanup is proven.
- No Tenn DB, Qdrant, news, memory, canonical financial truth, product runtime,
  parser, routing, or Strategy Lab status/UI mutations occur.
- `current_sidecar_available` remains false unless a later separate
  status-review task explicitly promotes it.

## Allowed Actions

- Read Tenn task cards, reports, Strategy Lab docs, and tests.
- Create this task card and report artifacts under the allowed report directory.
- Clone or copy QuantDinger into an isolated temporary sandbox.
- Apply the already proven upstream regime-detect guard patch in the temporary
  sandbox if the local upstream source does not already contain it.
- Start only the loopback-bound QuantDinger backend, Postgres, and Redis
  sandbox services needed for the probe.
- Issue one short-lived read/backtest-only token scoped to `R,B`, market
  `Crypto`, instrument `BTC/USDT`, and `paper_only=true`.
- Run bounded read-only health, market, klines, backtest, regime-detect, denial,
  zero-order, revoke, and cleanup checks.
- Persist sanitized request and response evidence without saving token secrets.

## Forbidden

- No live trading.
- No paper order placement.
- No broker credentials.
- No token secret persistence.
- No Tenn DB writes.
- No Qdrant writes.
- No news writes.
- No memory writes.
- No canonical financial truth writes.
- No Strategy Lab UI/status mutation.
- No `current_sidecar_available=true`.
- No transport integration.
- No Tenn parser, routing, runtime, model-config, or product-code edits.
- No production data access.
- No dependency installation inside Tenn.

## Hard Stops

Stop before runtime startup if:

- task-card validation fails
- registry overlap is unsafe
- target probe ports are already occupied
- Docker is unavailable
- the runtime cannot be loopback-only
- the probe would require broker credentials, token secret persistence, paper
  orders, live trading, production data, or Tenn store writes
- unresolved HIGH collision risk touches contested Tenn surfaces

Stop before declaring success if:

- regime detect fails
- exact payloads, candle counts, response bodies, revoke proof, zero-order
  proof, or cleanup evidence are not persisted
- runtime cleanup cannot be proven
- `current_sidecar_available` or Strategy Lab status/UI metadata is mutated

## Required Artifacts

Write:

- `README.md`
- `status.json`
- `runtime_proof.json`
- `payloads/health_response.json`
- `payloads/agent_health_response.json`
- `payloads/markets_response.json`
- `payloads/symbols_response.json`
- `payloads/klines_response.json`
- `payloads/backtest_request.json`
- `payloads/backtest_submit_response.json`
- `payloads/backtest_final_response.json`
- `payloads/regime_request.json`
- `payloads/regime_response.json`
- `payloads/denial_responses.json`
- `payloads/zero_order_proof.json`
- `payloads/revoke_response.json`
- `payloads/post_revoke_whoami_response.json`
- `cleanup_proof.json`
- `no_mutation_attestation.json`
- `validation.json`
- `diff-check.json`

All artifacts must redact token secrets while preserving token id, scopes,
market/instrument, HTTP statuses, request bodies, response bodies, candle counts,
order counts, revoke outcome, and cleanup evidence.
