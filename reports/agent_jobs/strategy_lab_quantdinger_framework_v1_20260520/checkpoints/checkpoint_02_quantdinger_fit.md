# M2 - QuantDinger Capability And Risk Fit

Scope: public QuantDinger and `quantdinger-mcp` materials only. No install, clone, Docker startup, token creation, MCP startup, broker connection, paper trade, or live trade was performed.

## Public Sources Read

- Official site: https://www.quantdinger.com/
- Official docs: https://www.quantdinger.com/docs.html
- GitHub README: https://github.com/brokermr810/QuantDinger
- MCP setup guide: https://raw.githubusercontent.com/brokermr810/QuantDinger/main/docs/agent/MCP_SETUP.md
- MCP server README: https://raw.githubusercontent.com/brokermr810/QuantDinger/main/mcp_server/README.md
- PyPI page: https://pypi.org/project/quantdinger-mcp/

## Confirmed Capabilities

### Backtesting

- QuantDinger documents deterministic backtesting with commission/slippage modeling, trade analytics, equity curves, strategy snapshots, and config snapshots.
- The MCP server README lists `submit_backtest`, `get_job`, `regime_detect`, and `submit_structured_tune`.
- Long jobs can stream or be polled through Agent Gateway job surfaces according to the setup guide and README.

Tenn fit now: suitable for a future isolated comparator if outputs are converted into Tenn artifacts with explicit limitations, data source, benchmark, and evidence labels.

### Strategy Execution

- QuantDinger supports Python-native `IndicatorStrategy` and `ScriptStrategy` patterns.
- It supports AI-assisted strategy drafting and strategy workspace operations.
- It also supports live strategy operation and order dispatch through exchange or broker adapters.

Tenn fit now: strategy code generation and execution must be blocked. Strategy ideas may be represented as Tenn artifacts only. Later sandbox-only backtest execution can be considered after a separate task card.

### Market And Regime Analysis

- Public docs describe AI market analysis, watchlists, charting, regime detection, market data, and multi-provider LLM analysis.
- The MCP server exposes market read tools such as `list_markets`, `search_symbols`, `get_klines`, and `get_price`.

Tenn fit now: suitable as non-canonical external context and comparator input. It must never override backend financial truth or Tenn source labels.

### MCP / API Surface

- QuantDinger exposes an Agent Gateway at `/api/agent/v1`.
- `quantdinger-mcp` wraps that gateway as MCP tools.
- PyPI lists `quantdinger-mcp` version `0.1.0`, released May 2, 2026.
- The official MCP README says the MCP package is additive and the Agent Gateway REST API remains source of truth.
- The MCP README says MCP exposes Read-class and Backtest-class tools only and no live trading from MCP.

Tenn fit now: the MCP path is viable for a future sandbox, but Tenn should put its own tool-policy client between the local llama/router and QuantDinger. Codex should not be the production path.

### Bot / Live Trading Surfaces

- QuantDinger supports live trading across crypto, IBKR, MT5, Alpaca, and related trading/broker surfaces.
- Docs describe autonomous trading bots, quick trade, live operations, broker accounts, exchange keys, and execution adapters.

Tenn fit now: blocked. These surfaces create HIGH risk and require a separate project, not a Strategy Lab report framework.

### Token / Permission Model

- Public docs describe agent token scopes: Read, Workspace, Backtest, Notify, Credentials, Trading.
- Public docs describe audit logs, token scoping, rate limits, idempotency, and paper-only defaults.
- Live execution requires both a token-level `paper_only=false` and server-level `AGENT_LIVE_TRADING_ENABLED=true`.
- Hosted path is described as paper-only and rejecting trading scope issuance.

Tenn fit now: use only read/backtest scopes in a future sandbox. Credentials and Trading scopes must be blocked. Workspace scope should be deferred until Tenn has schema validation and strategy-code quarantine.

### Docker / Runtime Footprint

- Public docs describe a Docker Compose stack with Flask API, PostgreSQL 16, Redis 7, Nginx-served Vue frontend, exchange/broker adapters, LLM adapters, notifications, OAuth, billing, and optional mobile/web clients.
- Default web UI is documented around `localhost:8888`; remote MCP HTTP examples use a configurable MCP port such as `7800`.

Tenn fit now: HIGH resource and collision risk if started inside Tenn runtime. A future sandbox must be isolated by worktree, process, ports, storage, and secrets.

## Suitability Matrix

| Capability | Now | Later | Blocked | Notes |
| --- | --- | --- | --- | --- |
| Public docs review | yes | yes | no | Already performed read-only. |
| Artifact schema design | yes | yes | no | Does not require runtime. |
| Read-only market metadata | no runtime now | yes in sandbox | no | Requires token and sidecar. |
| Backtest submission | no runtime now | yes in sandbox | no | Must be paperless/research-only and artifact-gated. |
| Parameter sweep / tuning | no runtime now | yes in sandbox | no | Requires deterministic inputs and resource limits. |
| Regime detection | no runtime now | yes in sandbox | no | Non-canonical comparator only. |
| Strategy workspace writes | no | maybe later | blocked until schema and quarantine | Could create code artifacts; high review burden. |
| Paper trading | no | Phase 11 review only | blocked now | User explicitly forbids setup now. |
| Credential management | no | separate security review | blocked now | Never expose broker keys to Codex or Tenn reports. |
| Live execution | no | separate project only | blocked | Must not be part of Strategy Lab integration. |

## Key Fit Conclusions

- Defensible safe path exists because QuantDinger offers read/backtest/regime tools without requiring live trading.
- QuantDinger should be treated as an external research sidecar and comparator, not Tenn's brain.
- Tenn should own artifact schemas, evidence labels, human review state, and financial-truth boundaries.
- The first useful phase should be a fit audit and isolated sandbox design, not runtime startup.
- Any result imported from QuantDinger must be labeled `external_tool_context` or equivalent non-canonical evidence, never `financial_truth`.

## DATA_MISSING

- No local QuantDinger install was inspected.
- No QuantDinger OpenAPI schema was parsed beyond public docs and README references.
- No real backtest output was produced.
- No resource measurement was performed.
- No legal/license review beyond public Apache/PyPI/package notes was completed.
