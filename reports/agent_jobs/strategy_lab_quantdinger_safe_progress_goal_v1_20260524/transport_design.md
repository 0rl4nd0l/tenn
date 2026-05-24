# QuantDinger Read-Only Transport Path

Generated: 2026-05-24T11:05:00Z

This is a design artifact only. It does not start QuantDinger, Docker, MCP, a broker, a background service, a scheduler, or any external network connection. It does not issue, store, or read credentials.

## Future Sidecar Contract

Any future real QuantDinger transport must be a separate approval-gated task card with exact allowed files and commands.

Minimum contract:

- loopback-only listener
- user-triggered smoke only; no automatic startup
- no stored token or credential file
- temporary test token only if explicitly approved by the task card
- scopes limited to read/backtest only
- `paper_only=true`
- default allowlist: Crypto / `BTC-USDT`
- write/trade scope denial tests before any useful result is accepted
- zero-order proof before and after smoke
- no Tenn DB, Qdrant, news, memory, canonical financial truth, parser routing, runtime/model, or service-state writes
- cleanup proof for containers, volumes, images, networks, temporary directories, listeners, and tokens

## Candidate Route Contracts

Status-only endpoint:

- `GET /api/cockpit/strategy-lab/status`
- may report historical smoke status
- may report `current_sidecar_available=false`
- must not start or probe the sidecar as a side effect
- must not report `current_sidecar_available=true` without same-task live runtime proof

Smoke report reference endpoint:

- `GET /api/cockpit/strategy-lab/qd-smoke-report`
- future endpoint only
- returns links/metadata for preserved smoke reports
- no runtime call
- no report promotion to canonical truth

Manual smoke action:

- future approval-gated action only
- not auto-run from Home or route rendering
- must show explicit preflight, port/listener baseline, W/T denial, zero-order proof, and cleanup proof

## Required Safety Tests Before Runtime Work

- status route never starts Docker or external processes
- historical `SMOKE_PASSED` never sets `current_sidecar_available=true`
- historical `SMOKE_PASSED` never sets `real_transport=true`
- live trading remains false
- paper order placement remains false
- canonical financial truth remains false
- store writes remain false
- W/T scope requests are denied
- zero orders before and after smoke
- cleanup closes all target ports and removes all temporary runtime artifacts

## Current Goal Decision

This goal stopped at historical metadata, repo-only artifact surfacing, tests, and this future contract. No sidecar runtime execution was performed.
