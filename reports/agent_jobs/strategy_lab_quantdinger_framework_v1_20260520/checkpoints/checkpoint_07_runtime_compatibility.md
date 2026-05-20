# M7 - Compatibility, Runtime, And Resource Plan

Design only. No runtime checks, Docker starts, service launches, or sidecar installs were performed.

## Local-First Compatibility

Tenn should keep QuantDinger replaceable by treating it as a sidecar behind:

- a Tenn-owned interface;
- a strict tool allowlist;
- schema-validated artifacts;
- raw-output quarantine;
- human review gates;
- no direct writes to Tenn stores.

## Expected Resource Impact

Based on public QuantDinger docs, a self-host stack includes Flask API, PostgreSQL 16, Redis 7, Nginx/Vue frontend, strategy runtime, broker/exchange adapters, and optional LLM/payment/notification integrations.

Likely impact:

- CPU: medium to high during backtests/sweeps.
- RAM: medium due Flask/Postgres/Redis plus result storage.
- GPU: not inherently required for backtests, but AI analysis may call LLM providers or local LLMs depending config.
- Disk: medium due market data, backtest outputs, Postgres volume, logs, and Docker images.
- Network: required for market data/providers unless using cached datasets.

## Docker And Process Isolation

Future sandbox must:

- run outside Tenn backend/Cockpit process tree;
- use a dedicated working directory;
- use dedicated Docker Compose project name if Docker is authorized;
- use dedicated volumes;
- use no production Tenn DB/Qdrant/memory mounts;
- use no Tenn secrets file;
- avoid host-level env leakage;
- have explicit cleanup and teardown plan.

## Port Conflicts

Known public QuantDinger defaults/examples:

- web UI around `localhost:8888`;
- MCP HTTP example around port `7800`;
- its internal backend/Compose ports are configurable.

Known Tenn surfaces include backend `8000`, local llama/router `8001` in current docs/memory, and Cockpit web ports in prior reports. Future sandbox must preflight:

- `ss -ltnp`;
- Tenn backend listener;
- Cockpit UI listener;
- llama.cpp/OpenClaw listener;
- Qdrant/Postgres/Redis ports;
- QuantDinger desired ports.

## Data Storage Location

Recommended future sandbox layout:

```text
reports/strategy_lab/quantdinger_sandbox/<job_id>/
  raw/
  normalized/
  artifacts/
  validation/
  logs/
```

Alternative if task-card scoped:

```text
reports/agent_jobs/<job_id>/strategy_lab/
```

Do not store sidecar Postgres volumes under Tenn production data roots. Do not store broker credentials in reports.

## No Production Store Mutation

Forbidden without separate task card:

- Postgres financial truth writes;
- Qdrant writes;
- memory SQLite writes;
- news store writes;
- parser/extraction/gold-label writes;
- source-registry writes;
- Cockpit route/config writes;
- Docker/systemd/env writes.

## Offline / Degraded Behavior

If sidecar unavailable:

- Strategy Lab shows `DATA_MISSING`;
- queued autonomous loops skip sidecar calls and write no fake results;
- Chat may explain that sidecar evidence is missing;
- Watchlist and Company pages continue to use Tenn-native evidence only;
- existing Tenn backend remains authoritative.

If sidecar output invalid:

- raw output is quarantined under approved report bundle;
- normalized artifact is not created or is `FAILED`;
- review queue shows schema failure;
- no downstream prompt context uses the invalid output.

## Replaceability

The Tenn interface should be named by capability, not vendor:

- `MarketDataResearchClient`
- `BacktestResearchClient`
- `RegimeResearchClient`
- `StrategyLabArtifactAdapter`

QuantDinger is one implementation. Vectorbt, qlib, Lean, or a Tenn-native runner can later replace it without changing Cockpit artifacts.

## DATA_MISSING

- No real CPU/RAM/Disk benchmark was run.
- No local QuantDinger Compose file was inspected.
- No sidecar port was bound.
- No storage volume was created.
