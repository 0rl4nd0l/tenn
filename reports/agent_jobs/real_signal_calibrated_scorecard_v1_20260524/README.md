# Real Signal Calibrated Scorecard Audit

Job: `real_signal_calibrated_scorecard_v1_20260524`
GitHub issue: #54
Lane: Evaluation
Execution mode: AUDIT ONLY
Branch: `audit/repo-hygiene-safe-audits-v1-20260525`
Pre-audit HEAD: `3c817a3672862c1d99a3d877d335dc4527711948`

## Decision

The issue-exact audit acceptance criteria are met as an audit/design closeout.
No product remediation landed and no Real Signal runtime scorecard was enabled.

Current repo evidence does not contain a named Real Signal implementation or an
existing `real_signal` scorecard artifact. The relevant behavior is dispersed
across heuristic scoring, deterministic evidence guards, UI actionability
mapping, news readiness, memory signal routing, extraction review quality flags,
and evaluation-spine profile separation.

## Confirmed

- `financial-engine_v2/backend/app/services/chat_quality_scorer.py` computes a
  composite chat quality metric from retrieval precision, model confidence, and
  session coherence. It is heuristic-only and does not encode provenance,
  DATA_MISSING, source-label, or canonical financial truth gates.
- `financial-engine_v2/backend/app/services/chat_evidence_guard.py` classifies
  broad claim families and marks missing or unsupported evidence with labels
  such as `market_data_missing`, `metric_extraction_missing`,
  `insufficient_for_recent_news`, `missing_required_evidence`, and
  `unsupported_or_not_verified`.
- `financial-engine_v2/backend/app/services/query_orchestrator.py` and
  `financial-engine_v2/backend/app/routes/cockpit_api.py` maintain source
  coverage status logic for `claim_verified`, `context_only`,
  `missing_required_evidence`, `no_hit`, and `unknown_unclassified`.
- `cockpit-ui/lib/cockpit-chat-actionability.ts` maps answer metadata and
  visible sources into UI states/gaps, including disabled suggested actions for
  market-data and metric-extraction gaps. These actions are not remediation.
- `cockpit-ui/lib/cockpit-news-actionability.ts` separates `DATA_MISSING`,
  `DEGRADED`, `UNRESOLVED`, `STALE`, `PARTIAL_SOURCE_CONTEXT`,
  `DUPLICATED`, and `SOURCE_READY`. `SOURCE_READY` is inspectable context, not
  verified financial truth.
- `financial-engine_v2/backend/app/services/memory_signal_router.py` extracts
  memo/news signals with confidence, materiality, persistence, source, and
  source_id, but `route_signals()` can mutate company/market memory stores.
  This audit did not execute those write paths.
- `docs/evaluation_spine_manifest_contract.md` requires named scorecard
  profiles and says memory context must not become financial truth.
- Existing issue-adjacent reports preserve DATA_MISSING where evidence is
  absent: confirmed metric extracted-payload scoring remains DATA_MISSING in
  `reports/agent_jobs/confirmed_metric_extracted_payload_scoring_audit_v1_20260525/README.md`.

## Inferred

- Tenn currently has pieces needed for a Real Signal scorecard, but no unified
  calibration gate that can safely decide whether an investment signal is
  actionable, inspectable context, weak context, or DATA_MISSING.
- The safest next implementation would be report-local and metadata-only:
  consume existing labels/statuses, emit a profile-scoped scorecard row, and
  refuse to treat heuristic confidence, memory context, or source-ready news as
  verified financial truth.

## Speculative

- A future Cockpit-visible scorecard may be useful, but it needs its own safe
  extension task and UI/backend contract review. This audit did not validate a
  product UI path.

## Scorecard proposal

Primary profile: `real_signal_readiness_v1`

Outcome classes:

- `ACTIONABLE_SIGNAL`: all required evidence gates pass, claim family
  requirements are satisfied, provenance is inspectable, freshness is proven
  when relevant, and no hard-stop label is present.
- `INSPECTABLE_CONTEXT`: source links/context are visible, but the evidence does
  not verify the claim or financial truth.
- `WEAK_CONTEXT`: context exists but is snippet-only, context-only, duplicated,
  stale, low-specificity, or otherwise insufficient for action.
- `DATA_MISSING`: required query, response, timestamp, extracted metric,
  market-data, source, payload, or route evidence is absent.
- `UNSUPPORTED_OR_NOT_VERIFIED`: a claim family is detected and required
  evidence is not satisfied.
- `DEGRADED_RUNTIME`: runtime/provider/search failure prevents a complete
  assessment.
- `REVIEW_ONLY`: scorecard row is audit/report-local and must not be displayed
  or treated as product remediation.

Hard stops:

- No score without a named `scorecard_profile`.
- No `claim_verified` result from LLM confidence, retrieval score, memory
  signal confidence, snippet context, source-ready news, or unclassified source
  labels.
- No collapse of inventory, source openability, route health, model confidence,
  or current extracted-payload accuracy into one pass rate.
- No mutation of memory/news/DB/Qdrant/runtime/config while computing the audit
  scorecard.
- If canonical financial rows or current extracted payloads are missing, emit
  `DATA_MISSING`, not a partial numeric truth score.

## Gap register

See `gap_register.json` for machine-readable rows. Main gaps:

- No named Real Signal scorecard implementation or report artifact existed
  before this issue-exact audit.
- Chat quality scoring can produce a high composite value from model confidence
  and retrieval scores without provenance or DATA_MISSING gates.
- Memory signal confidence/materiality is not claim verification and can touch
  memory stores if routed.
- News readiness proves inspectability/freshness only when its gates pass; it
  does not establish canonical financial truth.
- Confirmed metric extracted-payload accuracy remains DATA_MISSING until a
  generated extracted-payload artifact set exists.

## Recommended child task

Create `real_signal_scorecard_manifest_v1`: a report-local safe extension that
normalizes existing metadata into `real_signal_readiness_v1` rows. It should
consume only existing source-coverage, evidence-label, news-readiness,
confirmed-metric, and runtime status artifacts; write only report artifacts and
tests; and keep all hard stops above.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/real_signal_calibrated_scorecard_v1_20260524.md`: passed.
- `python3 scripts/agent_job_registry.py list-active`: passed before claim with `active_jobs: []`.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/real_signal_calibrated_scorecard_v1_20260524.md`: passed.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/real_signal_calibrated_scorecard_v1_20260524.md`: passed.
- `rg -n "Real Signal|real_signal|calibrated scorecard|real_signal_calibrated" . --glob '!node_modules/**' --glob '!.git/**'`: found only this issue-exact task card after creation.
- JSON validation, `git diff --check`, task-card `check-diff`, and registry release are recorded in `validation.json` and `diff-check.json`.

## DATA_MISSING

- No current product Real Signal runtime scorecard exists in repo evidence.
- No Cockpit-visible scorecard UI was validated or implemented.
- No current generated extracted-payload artifact set exists for confirmed
  metric payload scoring, so that part of Real Signal readiness remains
  DATA_MISSING.

## Hard-boundary compliance

No canonical truth, extraction routing, parser routing, extraction prompts, gold
labels, source-label semantics, production data, DB/Qdrant/news/memory stores,
model/runtime/service config, or product surfaces were changed.
