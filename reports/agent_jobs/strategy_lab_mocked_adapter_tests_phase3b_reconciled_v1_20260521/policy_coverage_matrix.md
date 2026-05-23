# Policy Coverage Matrix

| Area | Coverage | Result |
| --- | --- | --- |
| Authoritative schema | `strategy_lab_artifact_v1` in docs/schema/fixtures | Covered |
| Helper candidate | `strategy_lab_sidecar_artifact_v1` marked pre-envelope only | Covered |
| Hard flags | false truth/store/execution flags and `PENDING_REVIEW` | Covered |
| Evidence-backed types | `backtest_run`, `regime_breakdown` only | Covered |
| Held types | `parameter_sweep`, `risk_report`, `factor_test`, `portfolio_experiment` | Covered |
| Forbidden labels | `financial_truth`, generic `source-backed` | Covered |
| Tool allowlist | `list_capabilities`, `read_market_snapshot`, `submit_backtest`, `get_backtest_result`, `get_job`, `regime_detect` | Covered as mock-only |
| Conditional tools | `parameter_sweep`, `structured_tune`, `export_artifact` | Covered as default-hold or Tenn-owned local mock conversion only |
| Blocked surfaces | credentials, token/admin, paper/live/order/bot/kill-switch, Tenn stores, parser/gold-label, source registry | Covered |
| No-store writes | DB, Qdrant, news, memory, financial truth, parser labels, source registry, holdings, watchlist, thesis | Covered |
| Static import hygiene | no forbidden runtime/helper imports in Phase 3B test file | Covered |

No policy vector authorizes production data access, service startup, real transport, dependency installation, token issuance, store writes, paper execution, or live execution.
