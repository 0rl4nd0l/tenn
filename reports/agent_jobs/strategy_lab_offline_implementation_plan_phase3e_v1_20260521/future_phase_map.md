# Future Phase Map

These phases are planning suggestions only. They are not authorization to
implement, merge, start services, issue tokens, install dependencies, touch
stores, or execute trading behavior.

## Phase 3F: Consolidation Save Plan Only

Recommendation: run this next.

Scope:

- classify Phase 2/2B/3A/3B/3C files for save, merge, archive, or discard;
- decide how to preserve ignored report bundles;
- decide how to handle staged Phase 3A work;
- decide whether Phase 2B helper candidate should be saved as pending-review
  sidecar evidence or archived as superseded;
- produce a no-mutation or explicitly bounded save plan.

Forbidden:

- implementation;
- copying/merging files without explicit approval;
- runtime, store, dependency, token, or trading actions.

## Phase 3G: Production-Code Implementation Task-Card Draft Only

Scope:

- draft, but do not execute, a future task card for production-module code;
- define exact allowed files;
- define test files;
- define disabled-by-default flags;
- define no-store/no-trading invariants;
- define registry and validation gates.

Entry gate:

- Phase 3F must resolve consolidation readiness.

## Phase 3H: Offline Mocked Production-Module Tests

Scope:

- write tests for the future Tenn-owned client boundary using offline fixtures
  only;
- no real sidecar, network, MCP, Docker, token, dependency install, production
  data, runtime route, store write, or trading surface.

Entry gate:

- approved Phase 3G task card or equivalent.

## Phase 3I: No-Network Adapter Skeleton Only

Scope:

- implement a no-network, disabled-by-default adapter skeleton if separately
  approved;
- policy-before-dispatch and schema validation first;
- no real transport.

Entry gate:

- Phase 3H tests must exist and pass.

## Phase 3J: Isolated Real Sidecar Smoke

Scope:

- isolated real sidecar smoke only if separately approved;
- explicit no-store-write, no-production-data, no-token-issuance, and
  no-trading constraints;
- strict timeout/rate-limit and quarantine behavior.

Entry gate:

- real transport, credentials, tokens, runtime, and sidecar startup must be
  explicitly approved by a separate task card.

## Phase 4: Chat Workflow Design Only

Scope:

- design how Strategy Lab sidecar evidence could appear in chat or research
  workflows;
- no UI/backend integration;
- no artifact promotion;
- no source-registry or memory write.

## Phase 5: Strategy Lab UI Design Only

Scope:

- design pending-review UI states, quarantine displays, and human review affordances;
- no Cockpit implementation;
- no backend route implementation;
- no production data or stores.

## Non-Authorization Statement

None of these phase suggestions authorize:

- real adapter/client implementation;
- real API/MCP transport;
- QuantDinger/MCP/Docker startup;
- token issuance;
- dependency installation;
- runtime/backend/Cockpit integration;
- artifact persistence/store implementation;
- DB/Qdrant/news/memory/financial-truth writes;
- parser/gold-label changes;
- source-registry writes;
- production data access;
- broker/exchange/paper/live/order/bot/kill-switch behavior;
- autonomous loops or scheduled jobs.
