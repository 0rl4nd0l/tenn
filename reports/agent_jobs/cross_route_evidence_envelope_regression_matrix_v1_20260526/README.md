# Cross-Route Evidence Envelope Regression Matrix

Job: `cross_route_evidence_envelope_regression_matrix_v1_20260526`
Related issue: #104
Lane: Evaluation
Mode: AUDIT ONLY
Generated: 2026-06-01T20:19:21+10:00

## Decision

The audit can proceed as report-only without touching product files. Current
evidence shows the chat path has the strongest envelope propagation, but it has
visible-shell limits for secondary labels such as `local_news_context`. Home has
a parallel source-label contract that covers the issue-required labels but not
every backend-only taxonomy extension. Standalone News uses readiness states
that are visible but not normalized into the same `source_coverage_status` /
`claim_verified_source_count` envelope.

## Expected Envelope

The shared source-label taxonomy is `source_label_semantics_v1`. The matrix uses
these envelope fields as the minimum cross-route contract:

- `source_label_taxonomy_version`
- `evidence_labels`
- `source_label_counts`
- `source_coverage_status`
- `claim_verified_source_count`
- per-source `evidence_label`
- per-source `evidence_labels`
- per-source `claim_verified`
- route-specific `DATA_MISSING` / degraded reason payloads

## Allowed Values By Field

- `source_label_taxonomy_version`: `source_label_semantics_v1`
- `evidence_labels` / per-source `evidence_label`: values from
  `financial-engine_v2/shared/evidence_labels.py`, including
  `claim_verified`, `context_only`, `no_hit`, `operational_trace`,
  `local_personal_data`, `memory_context`, `external_web_context`,
  `local_news_context`, `financial_truth`, `financial_truth_numeric`,
  `degraded_runtime`, `missing_required_evidence`,
  `insufficient_for_recent_news`, and `unknown_unclassified`.
- `source_coverage_status`: chat metadata may use source-label values plus
  route states such as `no_visible_sources` and legacy `unknown_unclassified`.
- Home data state: `READY`, `PARTIAL`, `DEGRADED`, `DATA_MISSING`.
- Standalone News readiness reason: `DATA_MISSING`, `SEARCHING`, `DEGRADED`,
  `UNRESOLVED`, `STALE`, `PARTIAL_SOURCE_CONTEXT`, `SOURCE_READY`,
  `DUPLICATED`.

## Route Matrix Summary

| Route/surface | Status | Evidence |
| --- | --- | --- |
| Backend chat stream | PASS | `_build_chat_ui_metadata()` emits taxonomy version, label counts, labels, coverage status, and claim-verified count. |
| Chat SSE hydration | PASS | `chat-screen.tsx` maps streamed `sources` events into `evidenceLabel`, `evidenceLabels`, and `claimVerified`; done metadata is normalized into analyst metadata. |
| Saved chat/session reload | PASS | `normalizeSessionSources()` preserves source labels and claim verification; backend legacy assistant records default to `unknown_unclassified`. |
| Legacy backend chat routes | BOUNDARY / PARTIAL | `main.py` still mounts `routes/chat.py` at `/chat` and `/api`; `tenn_chat` emits source labels, but this is not the Cockpit Next.js chat route and does not expose the Cockpit routing metadata envelope. Do not use it as proof of Cockpit chat parity. |
| Chat analyst shell | PARTIAL / FOLLOWUP #175 | `terminal-message.tsx` renders degraded, missing evidence, no-hit, claim-verified, financial-truth, local-personal, memory, and context-only states from routing/source metadata. It does not render `local_news_context` as a distinct visible state, and expanded source rows display only the primary `evidenceLabel`, not all `evidenceLabels`; #87 remains the A2M-specific regression owner. |
| Recent sources drawer | PASS_WITH_SCOPE / PREDECESSOR #95 | `sources-drawer.tsx` is an attachment inventory, not a claim-verification drawer; it shows source identity and attach controls, not evidence labels. #95 is closed as a source-drawer semantics audit and should be treated as predecessor evidence rather than an active implementation owner. |
| Home source labels | PASS_WITH_SCOPE | `cockpit-home-contract.ts` maps the issue-required source labels to visible trust levels and blocks unsafe chat handoff for missing/no-hit/degraded/unknown/operational labels. Home does not currently expose every backend-only taxonomy extension such as `financial_truth_numeric` or `insufficient_for_recent_news`. |
| Home news panel and source drawer | PASS_WITH_SCOPE | Home maps backend evidence identity into `NewsItem` and source drawer displays data state, source label, evidence labels, and limits. It is not the same chat envelope shape. |
| News status endpoint | FAIL / FOLLOWUP #83/#175 | Backend `/api/cockpit/news/status` exposes a read-only status contract and explicitly reports `chat_synthesis=DATA_MISSING`; no current Cockpit UI consumer was found, while standalone News uses `/rag/query` instead. |
| Standalone News screen | FAIL / FOLLOWUP #175 | The screen shows `DATA_MISSING`, `DEGRADED`, `UNRESOLVED`, stale, duplicate, and snippet-only readiness, but it does not expose the shared source-label taxonomy, `source_coverage_status`, or claim-verified count; #83 remains the backend projection/materialization owner. |
| Announcement context runtime schema | FOLLOWUP #84 | Route parity remains blocked if `cockpit_announcement_context` runtime schema is missing or unavailable. |
| A2M visible evidence regression | FOLLOWUP #87 | Backend tests cover A2M missing/source-label cases, but #87 remains the concrete user-facing regression tracker for high-specificity claims with visible gaps. |

## Follow-Ups

- #83 owns news projection/materialization parity and should also own standalone
  News alignment to the shared evidence-envelope vocabulary plus UI consumption
  of the `/api/cockpit/news/status` contract.
- #84 owns runtime schema/openability uncertainty for announcement context.
- #87 owns the specific A2M chat visible-evidence regression and is the closest
  pre-existing owner for A2M-specific chat-visible evidence gaps.
- #95 is closed and should be cited as predecessor evidence for source-drawer
  semantics, not treated as an active follow-up owner.
- #175 was created by this audit as the bounded implementation owner for the
  chat-shell secondary-label and standalone News UI envelope visibility gaps.

## Boundaries

No source labels were changed. No UI/backend/runtime files were modified. No
DB, Qdrant, news, memory, canonical financial truth, parser, prompt, model,
GPU, or service config was touched.
