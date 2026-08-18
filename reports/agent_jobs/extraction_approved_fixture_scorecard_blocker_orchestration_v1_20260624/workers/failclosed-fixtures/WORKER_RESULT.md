I'll inspect the evidence surfaces to answer the fail-closed fixture questions. Let me start by reading the key files.
Now let me read the fixture files and the remaining portion of the failure rows:
Now let me read the remaining portion of the failure rows and the DXS and SEG rows:
Now I have all the evidence I need. Let me compile the WORKER_RESULT.md.

## WORKER_RESULT.md

```yaml
worker_id: failclosed-fixtures
task_tier: small
model: deepseek/deepseek-chat
decision_limit: evidence_only
summary: >-
  Three fail-closed payloads identified from the 15-fixture replay: ANZ (revenue
  ratio risk), DXS (mixed source scales + revenue ratio risk), SEG (wrapper
  disclosure missing). ANZ and DXS produced 9 non-null metrics each and were
  gated by scale/magnitude validation. SEG produced only 2 non-null metrics and
  was blocked at the wrapper stage. DXS and SEG had zero actual payload rows in
  the scorecard (9 and 7 respectively marked not_evaluated_no_actual_payload
  despite extractor producing 9 and 2 metrics). ANZ's 10 metrics were all
  quarantined (candidate_review_required) despite a successful extraction
  payload — the revenue ratio gate caught it post-extraction. SEG's root cause
  is wrapper failure (no Appendix 4D wrapper identified) preventing most metric
  extraction. DXS appears to be an entity-scope issue (REIT stapled structure)
  where the extracted payload scale differs from metric source scales.
findings: >-
  **ANZ_H_2025-03-31:** fail_closed with 9 non-null metrics. Error:
  `validation_gate:accepted_output_scale_magnitude_risk:metric_revenue_ratio_high`.
  Scale=millions, currency=AUD. Extraction produced a full payload (9/9
  non-null) but revenue magnitude (~$11.15B) triggered the revenue-ratio gate.
  Scorecard shows all 10 metrics as ambiguous_quarantined
  (CANDIDATE_REVIEW_REQUIRED) because no fixture-level scorecard could be
  generated without an accepted payload. Fixture is Claude API-verified (not
  hand-verified). Revenue field `operating income` from the income statement
  — revenue includes net interest income (bank accounting). The ratio trigger
  suggests the scale/magnitude gate flagged operating_cf ($47.5B) vs revenue
  ($11.15B) as anomalous. Classification: **scorecard/gold-review issue** —
  revenue expectation and ratio gate parameters may need adjustment for bank
  financials where revenue/CF ratios differ from industrial companies. Narrow
  fix is unsafe without confirming whether the gate ratio tolerances handle
  banking sector norms.

  **DXS_H_2025-12-31:** fail_closed with 9 non-null metrics. Error:
  `validation_gate:accepted_output_scale_magnitude_risk:mixed_metric_source_scales,payload_scale_differs_from_metric_source_scale,metric_revenue_ratio_high`.
  Scale=millions, currency=AUD. The extractor produced 9 non-null metrics but
  the scorecard has 9 `not_evaluated_no_actual_payload` entries (no actual
  payload in scorecard at all). Fixture is hand-verified (high confidence).
  DXS is a REIT stapled entity — the fixture notes identify multiple capex
  lines (PP&E vs investment property capex) and potential entity-scope
  ambiguity (consolidated stapled vs parent entity). The
  `payload_scale_differs_from_metric_source_scale` error indicates extracted
  metric-level scales may not match the payload-level scale (e.g., some
  metrics from tables vs document-level). The `mixed_metric_source_scales`
  confirms heterogeneous scale sources. Classification: **mixed entity
  scope / candidate-review issue** — the stapled entity structure means
  revenue and NPAT figures differ between consolidated and parent views.
  DXS fixture expects the consolidated figure. The mixed scales suggest the
  LLM picked up values from both scales. Unsafe for narrow fix without
  understanding whether entity-scope resolution or scale-validation logic
  needs changing. The fixture notes also flag `np_attributable` ambiguity
  (consolidated vs parent entity). Requires source-inspection of the actual
  extracted payload to see what values were captured.

  **SEG_H_2025-12-31:** fail_closed with only 2 non-null metrics. Error:
  `validation_gate:wrapper_missing_disclosure_evidence`. Scale=thousands,
  currency=AUD. The wrapper (Appendix 4D detection) failed to identify the
  disclosure wrapper, so most metrics (revenue, np_attributable, cash_flow items,
  shares_outstanding, net_debt) were not extracted (scorecard shows 7
  not_evaluated_no_actual_payload). Fixture is hand-verified (high confidence).
  SEG uses an Appendix 4D + IFRS interim financial report format — it is the
  only fixture in the set that has a full Appendix 4D + income statement + cash
  flow + balance sheet format for a non-mining operating company. The wrapper
  failure means the multipass pipeline couldn't find the Appendix 4D summary
  page to bootstrap context. Classification: **source-wrapper/evidence
  issue** — the wrapper detection logic doesn't recognize SEG's document
  layout. The fixture notes confirm this is exactly the diversity SEG was
  meant to test. The 2 non-null metrics extracted suggest some table-level
  extraction still fired (capex investing_cf maybe?) despite wrapper
  failure. Smallest source-inspection target: inspect the actual parsed
  document structure for SEG's PDF to understand why Appendix 4D wrapper
  detection failed. This is likely a document-structure/classifier fix, not
  a prompt or extraction change.
evidence_paths: >-
  - `reports/agent_jobs/extraction_approved_fixture_scorecard_blocker_orchestration_v1_20260624/failure_rows.json`
  (lines 3314-3360 for fail_closed_payloads, lines 2627-3172 for SEG/DXS
  not_evaluated rows)
  - `reports/agent_jobs/extraction_approved_15_fixture_replay_scorecard_v1_20260623/scorecard.json`
  (lines 81-99 for DXS 0/10, lines 216-233 for SEG 0/8 with 7 not_evaluated)
  - `reports/agent_jobs/extraction_approved_15_fixture_replay_scorecard_v1_20260623/replay_results.json`
  (DXS payload absent, SEG payload absent from accepted list)
  - `financial-engine_v2/backend/tests/eval_fixtures/ANZ_H_2025-03-31.json`
  (Claude API-verified, $11.15B revenue, bank sector)
  - `financial-engine_v2/backend/tests/eval_fixtures/DXS_H_2025-12-31.json`
  (hand-verified, REIT stapled entity, capex ambiguity, np_attributable
  consolidated vs parent ambiguity)
  - `financial-engine_v2/backend/tests/eval_fixtures/SEG_H_2025-12-31.json`
  (hand-verified, scale=thousands, Appendix 4D + IFRS format, full P&L +
  cash flow verified, SEG specific note on shares_outstanding 1000x scaling
  risk)
confidence: HIGH for SEG wrapper issue (clear signal from error code, fixture
  notes confirm layout diversity purpose); MEDIUM for DXS mixed-scale issue
  (error codes clear but root cause in the extracted payload itself is
  unverified because payload was not accepted into the scorecard); MEDIUM for
  ANZ revenue ratio risk (gate triggers are clear but whether the gate is
  correct for bank sector is unresolved — the fixture itself is not
  hand-verified).
risks: >-
  1. ANZ narrow fix: adjusting the revenue-ratio gate without confirming the
  gate is wrong for banking sector could silently accept wrong values in
  future bank extractions. The fixture is Claude API-verified only, so the
  gold values themselves are lower-confidence.
  2. DXS narrow fix: entity-scope resolution for stapled REITs could affect
  other REIT fixtures. If the fix adjusts scale-validation logic without
  understanding the mixed source scales, it may break correctly-extracted
  non-REIT payloads.
  3. SEG narrow fix: wrapper detection changes could have wide impact on
  all Appendix 4D documents. The fix must be scoped to the document
  classifier or wrapper-detection heuristic, not the extraction prompts.
  4. All three fixtures are HEAD-drift-sensitive—the scorecard shows
  source_pdf_exists=false, meaning the PDFs exist at configured paths but
  were not opened during the replay run (candidate-review mode). Any
  validation change must be replayed to confirm the fix.
recommended_next_action: >-
  1. For SEG: inspect the parsed document structure (Docling output or raw
  text) of the SEG PDF at
  `data/asx/docs/SEG/financial_performance/2026-02-18_half-year-fy26-financial-report_5fcfe1d9-6c17-416e-b978-89f109b41145.pdf`
  to identify why Appendix 4D wrapper detection fails. This is the cheapest,
  most isolated fix target.
  2. For ANZ: review the revenue-ratio gate parameters in
  `multipass_extraction.py` to confirm whether the
  `metric_revenue_ratio_high` threshold accommodates banking sector ratios
  (high operating CF relative to revenue). Cross-reference with a hand-verified
  bank fixture if possible.
  3. For DXS: extract the actual multipass payload
  (if stored/available from the replay run) to inspect which metrics had
  mismatched scales. Without the payload, root cause is speculative. Start
  with replay results to see if scale_validation=pass but
  metric_source_scales show mixed table vs document origins.
  4. After any fix, run a targeted regression on all 15 fixtures (not just
  the changed one) to confirm no regression on working fixtures.
stop_condition_hit: false
```
