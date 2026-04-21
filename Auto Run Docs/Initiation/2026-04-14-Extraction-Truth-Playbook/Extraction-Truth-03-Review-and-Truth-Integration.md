# Phase 03: Review and Truth Integration

This phase hardens the operator-review loop around the improved extraction system. The goal is not a broader Cockpit redesign; it is a contract-safe verification workflow where backend evaluation, provenance, confidence, and review outcomes are exposed consistently through backend APIs and reflected cleanly in Cockpit or the verification UI without any client-side reinvention of financial truth.

## Tasks

- [x] Audit the authoritative review and verification data contract before extending surfaces:
  - **Completed 2026-04-15**: Wrote `docs/ops/extraction-truth/phase-03-contract-map.md` mapping all backend fields to operator-visible states. Identified 4 inconsistencies: dual confidence fields (`confidence_overall` vs `confidence_metrics`), `abstain` vocabulary collision between gold eval and review decisions, parallel TUI/web surfaces, and `confidence_metrics` field name inconsistency in review items.

- [ ] Audit the authoritative review and verification data contract [COMPLETED ABOVE — original task body preserved for reference]:
  - Search existing backend and client integrations first: `/api/context/verification`, `/api/extraction-review/*`, `financial-engine_v2/cockpit/integrations/backend_api.py`, `financial-engine_v2/backend/app/services/extraction_review.py`, `financial-engine_v2/cockpit/ui/screens.py`, and `cockpit-ui/components/cockpit/verification/verification-screen.tsx`.
  - Write `docs/ops/extraction-truth/phase-03-contract-map.md` with YAML front matter (`type: reference`, `tags: [cockpit, verification, backend-authority]`) documenting which backend fields drive each operator-visible state and where the current contract is inconsistent.
  - Treat any missing data needed by the UI as a backend contract issue first, not as a reason to derive a second source of truth in the client.

- [ ] Normalize backend review and verification responses around the real operator workflow:
  - Reuse and extend existing backend models, services, and response payloads so extraction failures, low-confidence rows, run provenance, snippet evidence, wrong-queue items, and real-gold summaries can be consumed predictably.
  - Add only the fields needed for reviewability and traceability; avoid new storage layers or alternate aggregation services.
  - Preserve existing trust semantics such as `trusted`, `abstain`, `quarantine`, `ok`, and `ok_low_confidence` rather than introducing overlapping status vocabularies.

- [ ] Tighten Cockpit or verification UI behavior to reflect backend truth directly:
  - Reuse current verification screens and API clients instead of creating a separate review tool.
  - Make sure operators can see the most important backend-owned facts for a selected run or document: status, confidence, method provenance, trust outcome, snippet evidence, and review decision history.
  - Keep all calculations that affect truth or trust outcomes on the backend; the UI may sort, filter, and format only.

- [ ] Add targeted contract and integration coverage:
  - Extend backend tests around API models, review sessions, verification context, and any new serialization fields.
  - Extend Cockpit or `cockpit-ui` tests for the changed operator flow, especially run selection, review actions, real-gold summary rendering, and guarded keyboard or export behaviors.
  - Search for reuse first in `financial-engine_v2/backend/tests/test_cockpit_api_models.py`, `test_cockpit_api_action_execute.py`, `test_extraction_review_service.py`, and `cockpit-ui/tests/verification.spec.ts`.

- [ ] Prove the authoritative review loop end to end:
  - Boot the canonical backend, generate or reuse evaluated runs, load the verification surface, and walk at least one document from failure or low-confidence discovery to review-session inspection and persisted decision.
  - Verify that every displayed trust or confidence value can be traced back to a backend response or report artifact.
  - Export at least one review artifact and confirm it is generated from backend-owned data rather than client-local state.

- [ ] Capture the operator workflow and checkpoint the phase:
  - Write `docs/ops/extraction-truth/phase-03-review-workflow.md` with YAML front matter (`type: runbook`, `related: ['[[phase-03-contract-map]]', '[[phase-02-accuracy-report]]']`) describing the exact operator flow, backend endpoints involved, expected artifacts, and known limitations that remain acceptable.
  - If this phase reaches a working milestone, create the required milestone commit with tested evidence from the backend and UI verification steps.
