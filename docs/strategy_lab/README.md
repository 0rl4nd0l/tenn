# Strategy Lab

Status: read-only analytical subsystem, repo-artifact backed, pending review.

Strategy Lab is a non-live review surface for offline sidecar/comparator
evidence. It organizes QuantDinger sandbox proof into analyst-review semantics:
review queue items, experiment session envelopes, provenance refs, degraded-state
fixtures, cleanup/revoke proof, promotion blockers, and export packets.

## Confirmed

- Repo artifacts can represent Strategy Lab evidence without a database.
- `strategy_lab_artifact_v1` remains the authoritative artifact envelope.
- Clean QuantDinger re-probe evidence is reviewable as
  `VERIFIED_READ_ONLY_SIDECAR_SANDBOX_VIABILITY`.
- The Cockpit Strategy Lab route reads repository files only.
- UI status must preserve `PENDING_REVIEW`, `current_sidecar_available=false`,
  `execution_allowed=false`, `canonical_financial_truth=false`, and
  `real_transport=false`.

## Inferred

- A queue/session model is the safest next analyst workflow because it lets
  review work feel operational without creating a runtime or persistence layer.
- Review/export packets are useful handoff artifacts because they preserve
  provenance and blockers while staying outside Tenn stores.

## DATA_MISSING

- Human review owner and final review decision.
- Current sidecar runtime availability.
- Real transport retry, timeout, and unavailable behavior.
- Any persistent artifact store or promotion workflow.
- Post-commit ref for this maturation task until the work is committed.

## Current Safe Entry Points

- `review_queue_contract_v1.md`
- `experiment_session_envelope_v1.md`
- `review_packets_v1.md`
- `readonly_subsystem_boundaries_v1.md`
- `cockpit-ui/lib/strategy-lab-review-queue.ts`
- `GET /api/cockpit/strategy-lab/artifacts`

## Blocked

Do not promote Strategy Lab evidence into execution, current availability,
backend runtime orchestration, MCP/live transport, Tenn DB, Qdrant, news,
memory, parser, model/GPU config, source registry, or canonical financial truth
without a separate task card and explicit approval.
