# Intel Pulse Signals and Memory Capability Audit

## Decision

Do not wire live Signals or Memory data directly from the current frontend
panels. The safe next implementation is a backend-authoritative capability
contract:

1. The backend Intel Pulse response should explicitly describe the Signals and
   Memory stage capability state, including `available=false`, a stable reason,
   and the absence of a canonical read endpoint.
2. The `/intel-ops` UI should render the backend-provided capability state.
3. Live data wiring should remain blocked until the canonical Signals source
   and Intel Pulse Memory scope are selected.

This is narrower and safer than wiring counts or payloads from whichever
memory/signal surface is easiest to reach. It preserves the system contract:
backend owns truth and Cockpit presents backend-provided state.

## Current Evidence

| Evidence | Interpretation |
| --- | --- |
| `cockpit-ui/app/intel-ops/page.tsx:21-27` | The page loads a single Intel Pulse summary query through `getIntelPulse`; there is no per-stage Signals or Memory query. |
| `cockpit-ui/app/intel-ops/page.tsx:295-305` | Signals and Memory tabs render static `SIGNALS_UNAVAILABLE` and `MEMORY_UNAVAILABLE` panels. |
| `cockpit-ui/components/intel-ops/pipeline-ribbon.tsx:15-21` | Signals and Memory are always present in the default stage ribbon even before backend data arrives. |
| `cockpit-ui/lib/api-client.ts:1096-1110` | Intel Pulse client coverage is limited to `/api/cockpit/pulse` and `/api/cockpit/matrix`. |
| `cockpit-ui/lib/cockpit-types.ts:495-535` | Frontend types expose reserved `signal_count` and `memory_count`, but no stage capability payload or per-stage dataset. |
| `financial-engine_v2/backend/app/routes/cockpit_api.py:1320-1349` | Backend response model includes stats, pipeline, and failures only; no Signals/Memory stage payload or capability metadata. |
| `financial-engine_v2/backend/app/routes/cockpit_api.py:5662-5680` | Backend Intel Pulse route family exposes only `/pulse` and `/matrix`. |
| `financial-engine_v2/backend/app/services/cockpit_service.py:2692-2695` | Backend deliberately hard-codes `signal_count` and `memory_count` to zero until a canonical counter is wired. |
| `financial-engine_v2/backend/app/services/cockpit_service.py:2780-2790` | Backend pipeline already marks Signals and Memory stages as `unavailable`. |
| `reports/agent_jobs/system_task_frontend_wiring_status_audit_v1_20260513/frontend_wiring_map.md:80-83` | Prior audit classified Intel Pulse Signals/Memory as static unavailable placeholders. |
| `reports/agent_jobs/system_task_frontend_wiring_status_audit_v1_20260513/risk_register.md:14-15` | Prior risk register recommended labelling Intel Pulse partial until wired or hidden behind capability state. |
| GitHub issue search for `Intel Pulse Signals Memory` | Only #148 matched; no duplicate issue or PR was found in the current check. |

## Capability Options

### Option A: Keep Static Unavailable Panels

Status: reject as final state.

The current UI is honest, but it encodes the unavailable reason locally. That
leaves the product unable to distinguish deliberate backend-disabled capability
from stale frontend copy or missing backend wiring.

### Option B: Hide Signals and Memory Stages

Status: acceptable only if product wants the route to show currently actionable
stages only.

This reduces dead-space friction, but it can hide the roadmap state and makes
stage availability less inspectable unless the backend still exposes capability
metadata.

### Option C: Backend Capability Contract First

Status: recommended.

The backend already owns the Intel Pulse pipeline status and marks Signals and
Memory unavailable. A narrow contract can make that explicit without wiring
data:

- Extend the response with stage capability metadata, or extend each pipeline
  stage with a stable unavailable reason and optional `data_endpoint`.
- For Signals and Memory, return `available=false` with a reason such as
  `canonical_signal_feed_missing` or `memory_scope_not_selected`.
- Render those backend reasons in the UI.
- Add focused tests proving no synthetic Signals or Memory payload is shown.

### Option D: Wire Live Data Now

Status: blocked by DATA_MISSING.

Signals has no selected canonical feed on this surface. Memory has multiple
valid stores and scopes: company memory, market memory, user thesis memory, and
session/operational state. Wiring data before choosing the contract risks
conflating memory categories or making Cockpit define truth instead of rendering
backend-owned state.

## Recommended Follow-Up Slice

Create a safe-extension task for #148 with these boundaries:

- Backend:
  - Extend `IntelPulseStageHealth` or `IntelPulseResponse` with explicit
    stage capability fields.
  - Keep Signals and Memory unavailable by contract until canonical source and
    scope are selected.
  - Add backend tests for the unavailable capability payload.
- Frontend:
  - Render backend-provided unavailable reasons.
  - Keep or hide the stages based on the returned capability state, not hardcoded
    local copy.
  - Add a focused `/intel-ops` route/component test.
- Forbidden:
  - No synthetic Signals or Memory data.
  - No direct Cockpit DB/Qdrant access.
  - No memory writes.
  - No financial truth or source-label changes.

## DATA_MISSING

- Canonical Signals source for Intel Pulse is not selected.
- Intel Pulse Memory scope is not selected.
- Product choice between visible disabled stages and hidden unavailable stages
  is not selected.
- No live route smoke was needed or run in this audit-only slice.

## Contract Result

The current code is honest enough to avoid fabricated data, but the capability
contract is incomplete. The next safe fix is not to invent live data; it is to
make backend capability state explicit and make the UI consume that state.
