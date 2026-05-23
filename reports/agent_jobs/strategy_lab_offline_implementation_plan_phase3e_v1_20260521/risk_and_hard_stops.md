# Risk And Hard Stops

## Current Risk Classification

Risk is LOW/MEDIUM only while Phase 3E remains report-only. Risk becomes HIGH
and must stop if the work touches runtime, transport, stores, dependencies,
tokens, production data, source registries, parser labels, Cockpit, or trading
surfaces.

## Risks

| Risk | Evidence | Required control |
|---|---|---|
| Dirty worktrees masquerade as baseline | Phase 2/2B/3B/3C are untracked; Phase 3A is staged | require Phase 3F consolidation/save plan before production-module drafting |
| Helper output mistaken for authoritative artifact | Phase 2B uses `strategy_lab_sidecar_artifact_v1` | preserve `strategy_lab_artifact_v1` as authoritative; keep helper pre-envelope only |
| Simulated behavior mistaken for real sidecar behavior | Phase 3C sidecar unavailable and timeout are mock fixtures | keep real transport and runtime smoke separately approved |
| Store-write boundary creep | Strategy Lab artifacts are tempting to persist | keep pending-review report/quarantine separate from DB/Qdrant/news/memory/financial truth |
| Trading-capable sidecar creates accidental execution scope | QuantDinger can relate to trading workflows | deny broker/exchange/paper/live/order/bot/kill-switch surfaces by policy |
| Registry claim not available | Phase 3E `check-overlap` failed on unrelated Phase 3D dirty task card | do not claim; record warning; avoid unrelated dirty file changes |

## Hard Stops

Stop before:

- real adapter/client implementation;
- real API or MCP transport;
- editing `docs/strategy_lab/**`;
- editing `tests/strategy_lab/**`;
- merging, cherry-picking, committing, copying, staging, cleaning, stashing,
  resetting, removing, or unstaging Phase 2/3A/3B/3C files;
- importing or installing MCP/QuantDinger dependencies;
- installing `jsonschema` or any dependency;
- starting Docker;
- starting QuantDinger;
- starting MCP;
- issuing tokens;
- adding secrets or env config;
- broker/exchange/paper/live setup;
- paper/live/order/bot/kill-switch route;
- modifying Tenn runtime/backend/product code;
- modifying Cockpit;
- implementing an artifact store;
- DB/Qdrant/news/memory/financial-truth writes;
- parser/extraction/gold-label changes;
- source-registry writes;
- production data access;
- autonomous loops or scheduled jobs;
- modifying unrelated dirty files.

## Forbidden Until Separately Approved

The following must remain forbidden until a separate task card explicitly
authorizes them:

- real adapter/client;
- real API/MCP transport;
- QuantDinger/MCP/Docker startup;
- token issuance;
- dependency installation;
- runtime/backend/Cockpit integration;
- artifact persistence/store implementation;
- DB/Qdrant/news/memory/financial-truth writes;
- parser/gold-label changes;
- source-registry writes;
- production data;
- broker/exchange/paper/live/order/bot/kill-switch behavior;
- autonomous loops or scheduled jobs.

## Boundary Statement

Tenn remains the research brain and evidence/provenance authority. QuantDinger
remains a replaceable external read/backtest sidecar/comparator only. Strategy
Lab artifacts remain pending-review evidence, not canonical financial truth.
