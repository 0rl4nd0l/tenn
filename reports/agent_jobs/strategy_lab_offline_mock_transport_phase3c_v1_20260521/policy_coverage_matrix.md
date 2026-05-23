# Policy Coverage Matrix

| Area | Coverage | Result |
| --- | --- | --- |
| Authoritative schema | `strategy_lab_artifact_v1` copied and parsed | Covered |
| Helper candidate | `strategy_lab_sidecar_artifact_v1` pre-envelope only | Covered |
| Policy gate | Every mock fixture request passes policy before dispatch | Covered |
| Allowed mock operations | capabilities, market snapshot, backtest submit/result/job poll, regime detect | Covered |
| Default hold operations | `parameter_sweep`, `structured_tune` | Covered as `DATA_MISSING` |
| Local conversion | `export_artifact` only as local mock conversion with no store write | Covered |
| Denied scopes | paper/live scope, order fields, broker credentials, store-write intent | Covered |
| Blocked surfaces | credentials, token/admin, paper/live/orders/bot/kill-switch, Tenn stores, parser/gold labels, source registry | Covered |
| Artifact flags | false truth/store/execution flags and `PENDING_REVIEW` | Covered |
| Static import hygiene | stdlib-only Phase 3C test imports | Covered |

No Phase 3C policy fixture authorizes production data access, service startup, real transport, dependency installation, token issuance, store writes, paper execution, or live execution.
