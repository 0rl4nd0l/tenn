# Strategy Lab QuantDinger Clean Re-Probe Evidence Persistence v1

Generated: 2026-05-25T01:56:17Z

## Session Declaration

Lane: Evaluation
Branch: `migration/clean-runtime-baseline-reconstruct-v1`
Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
Execution mode: SAFE EXTENSION
Intended files: task card plus `reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/*`
Contested surfaces touched: none
Collision risk: MEDIUM for external sandbox startup; LOW for Tenn repo file overlap
Decision: VERIFIED READ-ONLY SIDECAR SANDBOX VIABILITY

Target system layer: external QuantDinger sidecar runtime plus Evaluation report artifacts. Tenn backend authority, canonical financial truth, memory, news, Qdrant, parser/routing/runtime/model config, and Strategy Lab status/UI were not changed. No llama-server or GPU runtime was spawned.

## Verdict

`VERIFIED_READ_ONLY_SIDECAR_SANDBOX_VIABILITY`.

The patched upstream QuantDinger runtime completed the bounded loopback-only read/backtest probe. Regime detect passed cleanly, exact sanitized request payloads and response bodies were persisted, candle counts were persisted, zero orders were proven, the short-lived token was revoked, and cleanup was proven.

`current_sidecar_available` remains false. This report proves sandbox viability only; it does not promote current Strategy Lab availability or integrate a real transport.

## Key Evidence

- Regime detect: HTTP 200, `high_volatility` / `High Volatility`, confidence `0.99`, segments `3`.
- Candle counts: `/klines` count `120`; regime service filtered count `91` from `2024-01-01 00:00:00` to `2024-03-31 00:00:00`.
- Backtest: final status `succeeded`, totalTrades `1`, trades_count `2`, equity points `91`.
- Zero orders: API/DB before `0/0`; API/DB after `0/0`.
- Token revoke: token id `2`, revoke HTTP `200`, DB status `revoked`, post-revoke whoami HTTP `401`.
- Cleanup: `cleanup_passed=true`; no target listeners, containers, volumes, networks, backend image, or temp sandbox remained.

## Persisted Payloads

- `payloads/token_issue_request.json`
- `payloads/token_issue_response_sanitized.json`
- `payloads/klines_response.json`
- `payloads/backtest_request.json`
- `payloads/backtest_submit_response.json`
- `payloads/backtest_final_response.json`
- `payloads/regime_request.json`
- `payloads/regime_response.json`
- `payloads/regime_candle_count_probe.json`
- `payloads/denial_responses.json`
- `payloads/zero_order_proof.json`
- `payloads/revoke_response.json`
- `payloads/post_revoke_whoami_response.json`

Token secrets and the admin JWT were redacted and were not written to artifacts.

## Notes

The first token issuance attempt used list values for `markets`/`instruments`; QuantDinger expects comma-separated strings and stored the list literally, so the market read was denied. That bad token was revoked and its evidence is preserved under `payloads/attempt1_list_payload_rejected/`. The successful probe used the documented string form.

## Files Changed

- `docs/agent_tasks/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525.md`
- `reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/README.md`
- `reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/status.json`
- `reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/runtime_proof.json`
- `reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/cleanup_proof.json`
- `reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/no_mutation_attestation.json`
- `reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/validation.json`
- `reports/agent_jobs/strategy_lab_quantdinger_clean_reprobe_evidence_persistence_v1_20260525/payloads/*`

## Save Recommendation

Save this as the evidence-persistent clean re-probe that moves QuantDinger from partial runtime proof to verified read-only sidecar sandbox viability. Do not use it to set `current_sidecar_available=true`; that remains a separate status-review/promote task.
