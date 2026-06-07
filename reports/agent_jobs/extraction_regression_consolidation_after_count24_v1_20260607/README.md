# Count-24 Regression Consolidation After Count-24

State: DONE_WITH_RISK.

Final decision: `NEEDS_SCALE_TABLE_HARNESS`.

Regressed: `MIXED`.

No confirmed rollback of canonical financial-truth guards was found. The mixed result is that current count-24 contains expected fail-closed behavior, unfixed variants, and one local-only integration gap.

## Objective

Stop the extraction loop by consolidating current count-24 failures against prior fixes, parked work, and canonical history. No random sample, count-24 rerun, count-32, broad extraction, or backfill was run.

## Evidence Used

- Current count-24 bounded validation artifacts under `reports/agent_jobs/extraction_count24_bounded_validation_v1_20260607/`.
- Current count-24 failure taxonomy artifacts under `reports/agent_jobs/extraction_count24_failure_taxonomy_v1_20260607/`.
- Merge-parking registry: `docs/agent_registry/merge_parking/REGISTRY.md` and parked entries.
- Recent extraction reports for PR #294, #297, #299, #301, #306, and #309.
- Git ancestry checks for named PR merge commits.

## Current Count-24 Baseline

- ok: 8
- ok_low_confidence: 0
- failed: 16
- exceptions: 0
- verdict: `COUNT24_FAILED_LOW_ACCEPTED_COUNT`
- first16 exact order match with post-PR301 count16: `True`
- first16 overlap with post-PR301 count16: `16`
- side-effect anomaly flags from artifact: `{"db_files_changed": false, "memory_mutated": false, "news_route_used": false, "qdrant_changed": false, "queues_clean_after_run": true, "risk_note_mutated": false, "source_pdfs_changed": false}`

## Count-24 Failure Gate Counts

| Gate | Count |
| --- | ---: |
| classifier_low_confidence:0.0 | 1 |
| source_noncandidate:board_change_notice | 1 |
| source_noncandidate:meeting_or_proxy_notice | 2 |
| source_noncandidate:operational_project_update | 1 |
| source_noncandidate:pre_results_segment_re_presentation | 1 |
| source_noncandidate:share_sale_or_gross_proceeds_announcement | 1 |
| validation_gate:announcement_date_period_end | 2 |
| validation_gate:insufficient_metrics | 1 |
| validation_gate:metric_label_mismatch | 1 |
| validation_gate:period_source_mismatch | 1 |
| validation_gate:scale_unknown | 4 |

## Evidence Table By Failure Family

| Family | Current docs | Consolidation result | Canonical / integration state |
| --- | ---: | --- | --- |
| scale_unknown | 4 | unfixed variants plus expected fail-closed behavior; not a confirmed regression of PR299/PR301. | PR #299 fixed specific smart-apostrophe/source-marker patterns; PR #301 added selected-table scale propagation. Coverage is partial. |
| scale_validation / suspect underscaled / overscaled | 3 | currently fail-closed, not accepted unsafe output; accepted row-ref provenance remains DATA_MISSING for ok rows. | PR #301/PR #306 contain selected-table scale and accepted-output containment/guards, but AZJ rounding policy remains unmodelled. |
| selected-table scale binding | 2 | DXC fails closed on net_operating_income->EBIT; LBL fails closed on announcement-date period; no accepted selected-table regression observed in count24. | Integrated through PR #301 lineage; tests exist around common metric source scale. |
| period/source mismatch | 1 | same expected fail-closed CTN variant, not regression. | Existing validation gate; no canonical repair for CTN source-period evidence yet. |
| announcement-date-as-period-end | 2 | expected fail-closed after canonical guard; improves truth safety even though ok count falls. | PR #306 half-year announcement-date fail-closed guard. |
| classifier_low_confidence | 1 | new known noncandidate variant; fixed locally, missing canonical/origin integration. | Local commit b5537f93 adds exact results-of-meeting -> meeting_or_proxy_notice; not in origin/migration. |
| true noncandidate leakage | 7 | expected fail-closed extraction behavior; candidate-pool/sample-quality issue remains because noncandidates consume validation slots. | PR #306 preserved source-noncandidate taxonomy; current failures are fail-closed, not accepted leakage. |
| meeting/proxy notices | 3 | EQR/QGL expected fail-closed; MQR was unfixed variant now local-only fixed. | PR #306 for Notice of Meeting/AGM; local b5537f93 for results-of-meeting variant. |
| director-interest notices | 0 | not present in current count24. | PR #306 adds director_interest_notice and scorecard taxonomy test. |
| board-change notices | 1 | expected fail-closed. | Canonical source-noncandidate gate existed before current count24; preserved by PR #306. |
| operational project updates | 1 | expected fail-closed. | Canonical source-noncandidate gate existed before current count24; preserved by PR #306. |
| share-sale/gross-proceeds notices | 1 | expected fail-closed. | Canonical source-noncandidate gate existed before current count24; preserved by PR #306. |
| pre-results or segment re-presentation docs | 1 | expected fail-closed. | Canonical source-noncandidate gate existed before current count24; preserved by PR #306. |
| Appendix 4D/4E wrapper metric minimum | 1 | no current count24 regression; keep GPT as fixed control harness case. | PR #294 wrapper gate and PR #297 payload construction repair are canonical ancestors. |
| insufficient_metrics | 1 | new variant/policy gap; safe fail-closed with zero canonical metrics. | none |
| accepted-output risks like Net operating income -> EBIT | 1 | expected fail-closed; no current accepted-output regression for DXC. | PR #301 rejects Net operating income as canonical EBIT. |

## Key Findings

1. DXC/HUB/LBL are not current accepted-output regressions. DXC fails closed with `metric_label_mismatch`, and HUB/LBL fail closed with `announcement_date_period_end` after PR #306.
2. True noncandidate families are fail-closed, not accepted leakage. They still pollute the validation denominator and should be separated in candidate-pool reporting rather than fixed by loosening gates.
3. MQR `results-of-meeting` was a new meeting-material variant. It is fixed by local commit `b5537f93`, but that commit is not in `origin/migration/clean-runtime-baseline-reconstruct-v1` yet.
4. The repeated hard blocker is scale/table-source evidence: WHC, AZJ, EDU, and NIC. Prior PR #299/#301 scale fixes were partial pattern repairs, not a general solution.
5. Parked extraction work exists, but no parked parent branch is safe to merge as a bulk answer. The high-risk truth-gates parent batch must be decomposed before any integration decision.

## Fixed Regression Harness Manifest

Created: `reports/agent_jobs/extraction_regression_consolidation_after_count24_v1_20260607/harness_manifest.json`.

- cases: 22
- mode: report-local manifest only
- executed: false
- includes current count-24 failures, prior GPT Appendix 4D target, and clean controls from current accepted rows.

## Fixes / Tests Added

No new consolidation-phase code fix was made. The earlier count-24 failure-taxonomy closeout was committed first:

- commit: `b5537f933f2b7b31a1cab8dea0f4204ba2ac8360`
- scope: exact `results-of-meeting` source noncandidate exclusion plus focused test
- origin integration: missing

## Another Sample Decision

Another count-24 sample is not justified now. Count-32 remains blocked and requires a separate approval packet.

## Next High-Leverage Repair Plan

1. Use the fixed harness manifest to run a targeted scale-table/source-evidence audit for WHC, AZJ, EDU, and NIC only.
2. Inspect source text/table headers read-only; do not run a random sample.
3. Implement at most one narrow source-bound scale propagation fix if the same pattern appears in at least two harness cases.
4. If no repeated source-bound pattern exists, keep count-24 rerun blocked and produce the next exact repair prompt.

## Final Decision

`NEEDS_SCALE_TABLE_HARNESS`

## DATA_MISSING

- Direct source-PDF text/table inspection for WHC, AZJ, EDU, NIC, JAY, and NIC document-family policy remains DATA_MISSING in this consolidation phase.
- Accepted-output row refs/provenance/extraction_run_id remain DATA_MISSING for count24 ok rows.
- MQR results-of-meeting fix is not in origin/migration at this time.
- Parked high-risk parent truth-gates batch contents were not merged or decomposed.
- No runtime service loaded-commit proof was gathered because no runtime extraction was executed.

## Project Memory Save Recommendation

Save that count24 did not show a confirmed guard regression: DXC/HUB/LBL now fail closed, noncandidate failures are expected fail-closed/sample-quality issues, MQR results-of-meeting is local-only, and the next high-leverage path is a WHC/AZJ/EDU/NIC scale-table harness before any new count24 packet.

## Exact Next Recommended Prompt

```text
Using reports/agent_jobs/extraction_regression_consolidation_after_count24_v1_20260607/harness_manifest.json, run a targeted scale-table/source-evidence audit only for WHC, AZJ, EDU, and NIC. Do not run count-24/count-32/random samples/broad extraction/backfill. Inspect source text/table headers read-only, then implement at most one narrow source-bound scale propagation fix with focused tests if the same pattern appears in at least two harness cases; otherwise produce the exact repair prompt and keep count-24 rerun blocked.
```

## Unsafe Actions Avoided

- count-24 rerun not run
- count-32 not run
- random sample not run
- broad extraction/backfill/full ticker extraction not run
- DB/Qdrant/news/memory mutation not run
- source PDF edits not run
- prompt/gold-label/runtime/schema changes not run
- dirty parent branches not merged
- unrelated dirt not cleaned/stashed/reset/deleted
