# M4 - MCP Runtime And Tool Policy Design

This is a design only. No MCP server, QuantDinger stack, Docker service, broker connection, token, or runtime process was started.

## Safe Runtime Pattern

```text
Cockpit / Tenn orchestrator
  -> local llama/router
  -> Tenn tool policy/client
  -> QuantDinger sidecar API or MCP
  -> structured Strategy Lab artifact
  -> Tenn evidence bundle
  -> human review queue
```

Codex is not the production runtime path. Codex may write task cards and design reports only.

## Tool Allowlist

Allowed in future sandbox phases only:

- `whoami`
- `list_markets`
- `search_symbols`
- `get_klines`
- `get_price`
- `list_strategies`
- `get_strategy`
- `submit_backtest`
- `get_job`
- `regime_detect`
- `submit_structured_tune`

Optional later, only after schema quarantine:

- workspace strategy draft/create/edit tools, if they exist and are scoped to non-executing research artifacts.

## Blocked Tools And Surfaces

Always blocked for this framework until a separate approved project exists:

- credentials scope
- trading scope
- quick trade
- live strategy start
- bot start/stop when connected to broker/exchange execution
- broker account connection
- exchange API key testing
- live order placement
- paper order placement in phases 0-10
- server flag changes such as `AGENT_LIVE_TRADING_ENABLED=true`
- any QuantDinger admin action that changes users, billing, credentials, or global permissions
- any tool that writes Tenn DB, Qdrant, memory, parser, extraction, gold labels, or financial truth

## Permission Ladder

| Level | Name | Allowed | Human Gate |
| --- | --- | --- | --- |
| 0 | Docs only | Read public docs and design schemas | none |
| 1 | Isolated sandbox inventory | Inspect sidecar config without tokens | explicit task card |
| 2 | Read-only token | Market/symbol/price reads only | token issuance by human |
| 3 | Backtest token | Submit bounded backtests and get jobs | per-job review or bounded batch approval |
| 4 | Workspace draft | Create non-executing strategy drafts | human approval plus code quarantine |
| 5 | Paper execution review | Paper-only execution review, no broker keys in Tenn | separate task card, explicit approval |
| 6 | Live execution | Not part of Strategy Lab | separate project; blocked here |

Default for Tenn Strategy Lab: Level 0 until a future task card authorizes Level 1.

## Paper-Only Defaults

- Paper-only is necessary but not sufficient.
- Phases 0-10 must block even paper execution because the user explicitly forbids paper setup for this task.
- Phase 11 may design paper-execution review only; it must not perform setup unless separately authorized.
- Live execution remains Phase 12 blocked/separate project.

## Logging And Audit Requirements

Every future tool call must produce:

- Tenn request ID.
- Strategy Lab job ID.
- Human approval reference if required.
- Tool name.
- Tool scope.
- Sidecar base URL alias, not a secret.
- Token scope hash or redacted token reference.
- Input parameters.
- Idempotency key.
- Sidecar run/job ID.
- Raw output hash.
- Raw output artifact path.
- Schema validation result.
- Evidence labels.
- Result status.
- `DATA_MISSING` rows.
- Failure classification.

## Schema Validation

Inputs:

- validate ticker/symbol format;
- validate date ranges;
- cap time range and frequency;
- cap universe size;
- require benchmark;
- require fees/slippage assumptions;
- reject missing data source;
- reject execution mode fields.

Outputs:

- validate against `artifact_schema_v1.md`;
- require provenance;
- require limitations;
- require benchmark;
- require result status;
- require evidence label;
- require non-canonical truth flags.

## Rate Limits And Resource Caps

Initial suggested caps for future sandbox:

- maximum 1 active QuantDinger job per Tenn Strategy Lab job;
- maximum 5 backtests per parameter sweep in first sandbox;
- maximum date range: 5 years daily or 18 months intraday;
- maximum universe: 25 symbols unless explicit task card widens it;
- maximum raw artifact size: 25 MB per result;
- timeout: 15 minutes per backtest in first sandbox;
- retry: one retry only for transient transport failures.

## Failure Handling

| Failure | Tenn Response |
| --- | --- |
| Sidecar unavailable | `DATA_MISSING`, no fallback result fabrication |
| Token rejected | `BLOCKED`, ask human for sandbox token |
| Tool not allowed | `BLOCKED_BOUNDARY_RISK` |
| Live/paper execution requested | `blocked_execution_surface` evidence label |
| Output schema invalid | artifact rejected, raw output quarantined |
| Backtest failed | artifact `result_status=FAILED`, keep logs |
| Partial data | artifact `result_status=DATA_MISSING` or `COMPLETE_WITH_LIMITATIONS` if later allowed |
| Resource cap exceeded | fail closed and write review item |

## Human Approval Gates

Required approvals:

- connecting to any sidecar instance;
- issuing any token;
- adding Backtest scope;
- running any batch of more than one backtest;
- allowing Workspace scope;
- exposing results in Cockpit product surfaces;
- writing to memory;
- using user holdings;
- using any broker/exchange credential;
- paper execution;
- live execution.

## Non-Negotiable Boundaries

- QuantDinger is never canonical financial truth.
- Tenn backend remains authority for financial truth, retrieval, and memory.
- QuantDinger UI is admin/debug only, not the main Cockpit UI.
- No sidecar result may write Postgres, Qdrant, memory, or gold labels.
- No trade path is authorized by this framework.
