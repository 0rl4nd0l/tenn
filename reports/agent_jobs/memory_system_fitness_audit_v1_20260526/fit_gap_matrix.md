# Fit/Gap Matrix

| Requirement | Current fit | Gap | Recommendation |
|---|---|---|---|
| Financial truth remains authoritative | Good. Docs and contracts separate Postgres financial truth from reasoning memory. | None found in inspected audit scope. | NO_FOLLOWUP for architecture split. |
| Company memory is qualitative and evidence-bound | Good. Forbidden financial metric signal types are rejected, dedupe/reinforce/supersede/contradict/expire flows exist. | Existing validation is not a whole-system harness. | DEFER: fixture-based memory fitness harness. |
| Market memory is qualitative sector/macro context | Good. Forbidden metric types are rejected and retrieval returns sector + macro context. | Linked-ticker contamination checks exist, but route/source-plan and staleness coverage is incomplete. | DEFER: extend fixture harness and integrity audit. |
| User thesis memory is user-owned and confirmation-gated | Good. Proposal, confirm, reject, and apply states exist; apply requires confirmed status. | Live UI/BFF confirmation workflow was not proven in this audit. | DEFER: route parity smoke for memory/thesis BFF. |
| Preference memory is separate from thesis/company/market memory | Partial. StateStore user preferences and route-alias confirmation tests exist; learned chat preferences are separate JSON. | Architecture docs do not fully inventory learned chat preferences or their governance. | DEFER: preference memory ownership and operator-control audit. |
| Session continuity exists without becoming proof | Adequate. Session memory is optional and prior context is documented as background only. | OpenViking availability and live root were not verified; session summaries are not automatic. | DATA_MISSING plus DEFER: read-only runtime root/status probe and session cleanup controls. |
| Staleness, expiry, cleanup, contamination controls | Partial. Qualitative rows have active/expired status and filtering; StateStore cleanup exists. | Event logs, MemoryStore archives, old alerts, entity-observation circularity, and live root ownership need stronger controls. | DEFER: stale/session/entity-observation control issue. |
| Cockpit UI exposes memory capabilities | Partial. Web Memory tab and BFF routes exist; tests cover mocked workflows. | No live no-store route parity smoke was run. | DEFER: live read-only UI/BFF contract smoke. |
| Observability proves read/write behavior | Partial. Read/write JSONL events are emitted. | Event writes are fail-open and no schema/rotation/health gate was found. | DEFER: memory event log health and schema gate. |
| Validation covers architecture fitness | Weak. Existing `audit_memory_integrity.py` is useful but narrow. | No single harness covers assembler source plans, read filtering, thesis gating, preferences, event traces, session degradation, and UI route parity. | DEFER: build non-mutating fixture-based memory fitness harness. |

## Confirmed Strengths

- The architecture preserves a meaningful distinction between truth, reasoning memory, user-owned thesis memory, session memory, operational state, retrieval indexes, and workspace artifacts.
- Company and market memory have explicit financial-metric write guards.
- User thesis memory has an explicit confirmation gate.
- Cockpit memory management surfaces are documented as clients over backend APIs.

## Main Risks

1. Validation does not yet prove the whole memory system behaves correctly across source plans, stores, BFF routes, and UI workflows.
2. Live runtime root ownership is unverified in this audit.
3. Event logs are best-effort and can silently fail, limiting operator confidence.
4. Preference memory is partly outside the main ownership map.
5. Session and entity-observation loops have documented stale/circularity risks.
