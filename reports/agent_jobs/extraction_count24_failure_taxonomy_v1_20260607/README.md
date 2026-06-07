# Count-24 Failure Taxonomy Audit

State: DONE_WITH_RISK.

Mode: AUDIT FIRST with one narrow SAFE_EXTENSION.

## Objective

Audit the 16 failed documents from the count-24 bounded validation and identify the next narrow repair path without rerunning samples or running backfill.

## Source Evidence

- `reports/agent_jobs/extraction_count24_bounded_validation_v1_20260607/sample_manifest.json`
- `reports/agent_jobs/extraction_count24_bounded_validation_v1_20260607/sample_results.json`
- `reports/agent_jobs/extraction_count24_bounded_validation_v1_20260607/classification.json`
- `reports/agent_jobs/extraction_count24_bounded_validation_v1_20260607/side_effect_audit.json`
- `reports/agent_jobs/extraction_count24_bounded_validation_v1_20260607/validation.json`

## Count-24 Baseline

- ok: 8
- ok_low_confidence: 0
- failed: 16
- exceptions: 0
- verdict: `COUNT24_FAILED_LOW_ACCEPTED_COUNT`
- side-effect anomaly flags: `{"db_files_changed": false, "qdrant_changed": false, "queues_not_clean_after_run": false, "source_pdfs_changed": false, "unexpected_git_paths": []}`

## Failure Taxonomy Table

| Ticker | Document ID | Title | Source path | Document class | Failure gate | Buckets | Expected/safe assessment |
|---|---|---|---|---|---|---|---|
| WHC | `9640d9f1-a45b-492d-8df5-9bad0f46431c` | 2022-09-21_2022-annual-report_9640d9f1-a45b-492d-8df5-9bad0f46431c.pdf | `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/WHC/financial_performance/2022-09-21_2022-annual-report_9640d9f1-a45b-492d-8df5-9bad0f46431c.pdf` | financial_report | `validation_gate:scale_unknown` | eligible report with missing scale evidence | safe fail; eligible annual report needs source scale evidence before acceptance |
| EQR | `aadead44-11f3-46d5-933b-6f2c8792e6f9` | 2022-10-21_notice-of-annual-general-meeting-proxy-form_aadead44-11f3-46d5-933b-6f2c8792e6f9.pdf | `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/EQR/financial_performance/2022-10-21_notice-of-annual-general-meeting-proxy-form_aadead44-11f3-46d5-933b-6f2c8792e6f9.pdf` | meeting_or_proxy_notice | `validation_gate:source_noncandidate:meeting_or_proxy_notice` | true noncandidate | expected safe fail; meeting/proxy notice is a true noncandidate |
| MAH | `05a85ffc-25cb-49a7-b770-df5e08f88ed9` | 2022-06-17_update-in-relation-to-mt-morgans-gold-project_05a85ffc-25cb-49a7-b770-df5e08f88ed9.pdf | `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/MAH/financial_performance/2022-06-17_update-in-relation-to-mt-morgans-gold-project_05a85ffc-25cb-49a7-b770-df5e08f88ed9.pdf` | operational_project_update | `validation_gate:source_noncandidate:operational_project_update` | true noncandidate | expected safe fail; project update is a true noncandidate |
| FCL | `e7290bdf-2865-468c-9a9b-9fcc6a61d446` | 2022-10-24_fineos-board-changes_e7290bdf-2865-468c-9a9b-9fcc6a61d446.pdf | `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/FCL/financial_performance/2022-10-24_fineos-board-changes_e7290bdf-2865-468c-9a9b-9fcc6a61d446.pdf` | board_change_notice | `validation_gate:source_noncandidate:board_change_notice` | true noncandidate | expected safe fail; board-change notice is a true noncandidate |
| AZJ | `488d6f1a-0180-4fca-8dcf-c4cdfc0f342e` | 2025-08-18_aurizon-network-pty-ltd-full-year-report_488d6f1a-0180-4fca-8dcf-c4cdfc0f342e.pdf | `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/AZJ/financial_performance/2025-08-18_aurizon-network-pty-ltd-full-year-report_488d6f1a-0180-4fca-8dcf-c4cdfc0f342e.pdf` | unknown_document | `validation_gate:scale_unknown` | eligible report with scale validation issue, parser/table coverage gap | safe fail; values were extracted but scale remained source-unproven |
| HRZ | `ea1b1f56-702e-4e23-a2fe-36c8136cf99c` | 2024-04-29_vox-shares-sold-2-93m-gross-proceeds_ea1b1f56-702e-4e23-a2fe-36c8136cf99c.pdf | `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/HRZ/financial_performance/2024-04-29_vox-shares-sold-2-93m-gross-proceeds_ea1b1f56-702e-4e23-a2fe-36c8136cf99c.pdf` | share_sale_or_gross_proceeds_announcement | `validation_gate:source_noncandidate:share_sale_or_gross_proceeds_announcement` | true noncandidate | expected safe fail; share-sale/gross-proceeds notice is a true noncandidate |
| MPL | `bf82c108-980b-4792-ad76-838c3fe446ca` | 2026-02-13_re-presentation-of-segment-results-and-terminology-changes_bf82c108-980b-4792-ad76-838c3fe446ca.pdf | `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/MPL/financial_performance/2026-02-13_re-presentation-of-segment-results-and-terminology-changes_bf82c108-980b-4792-ad76-838c3fe446ca.pdf` | pre_results_segment_re_presentation | `validation_gate:source_noncandidate:pre_results_segment_re_presentation` | true noncandidate | expected safe fail; pre-results segment re-presentation is a true noncandidate |
| DXC | `f8a24788-dbe0-48f7-ad41-654f2c8a3845` | 2025-08-11_fy25-results-presentation_f8a24788-dbe0-48f7-ad41-654f2c8a3845.pdf | `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/DXC/financial_performance/2025-08-11_fy25-results-presentation_f8a24788-dbe0-48f7-ad41-654f2c8a3845.pdf` | unknown_document | `validation_gate:metric_label_mismatch:ebit:net_operating_income` | parser/table coverage gap | expected safe fail; EBIT candidate mapped from net operating income |
| HUB | `419bcca8-213e-4706-8962-8e3bd8adf091` | 2024-02-20_hub24-1hfy24-interim-financial-report-and-appendix-4d_419bcca8-213e-4706-8962-8e3bd8adf091.pdf | `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/HUB/financial_performance/2024-02-20_hub24-1hfy24-interim-financial-report-and-appendix-4d_419bcca8-213e-4706-8962-8e3bd8adf091.pdf` | unknown_document | `validation_gate:announcement_date_period_end:period_type=H:period_end=2024-02-20:title_date=2024-02-20:leading_title_date` | period/source mismatch | expected safe fail; half-year period_end equalled announcement title date |
| LBL | `551c6b84-1053-405c-a833-4ecc018e2045` | 2026-02-20_1h-fy26-results-presentation_551c6b84-1053-405c-a833-4ecc018e2045.pdf | `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/LBL/financial_performance/2026-02-20_1h-fy26-results-presentation_551c6b84-1053-405c-a833-4ecc018e2045.pdf` | unknown_document | `validation_gate:announcement_date_period_end:period_type=H:period_end=2026-02-20:title_date=2026-02-20:leading_title_date` | period/source mismatch | expected safe fail; half-year period_end equalled announcement title date |
| CTN | `dec0b5f1-e6d2-48d8-ad9d-16ffd540ee39` | 2022-04-28_quarterly-activities-appendix-5b-cash-flow-report_dec0b5f1-e6d2-48d8-ad9d-16ffd540ee39.pdf | `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/CTN/financial_performance/2022-04-28_quarterly-activities-appendix-5b-cash-flow-report_dec0b5f1-e6d2-48d8-ad9d-16ffd540ee39.pdf` | unknown_document | `validation_gate:period_source_mismatch:payload=Q:source=A:annual_report_title` | period/source mismatch | expected safe fail; payload/source period type mismatch |
| EDU | `ac3c9ab0-e01a-4996-95f9-6466388ddc9c` | 2024-02-27_2023-annual-report_ac3c9ab0-e01a-4996-95f9-6466388ddc9c.pdf | `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/EDU/financial_performance/2024-02-27_2023-annual-report_ac3c9ab0-e01a-4996-95f9-6466388ddc9c.pdf` | financial_report | `validation_gate:scale_unknown` | eligible report with scale validation issue | safe fail; annual report extraction lacks source-bound scale |
| NIC | `50398d3d-27f7-4d9e-8a26-a2d69f128a1c` | 2025-08-11_half-year-results-webcast-details_50398d3d-27f7-4d9e-8a26-a2d69f128a1c.pdf | `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/NIC/financial_performance/2025-08-11_half-year-results-webcast-details_50398d3d-27f7-4d9e-8a26-a2d69f128a1c.pdf` | financial_report | `validation_gate:scale_unknown` | document-family policy gap, eligible report with missing scale evidence | safe fail; title suggests webcast-details policy gap and no scale evidence |
| QGL | `5eaa9900-0749-448a-a7bc-a5af19eddb23` | 2025-10-28_notice-of-annual-general-meeting-proxy-form_5eaa9900-0749-448a-a7bc-a5af19eddb23.pdf | `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/QGL/financial_performance/2025-10-28_notice-of-annual-general-meeting-proxy-form_5eaa9900-0749-448a-a7bc-a5af19eddb23.pdf` | meeting_or_proxy_notice | `validation_gate:source_noncandidate:meeting_or_proxy_notice` | true noncandidate | expected safe fail; meeting/proxy notice is a true noncandidate |
| JAY | `04438122-c607-4c53-bb41-2e3864c06479` | 2023-04-11_q3fy23-update-march-record-trips-and-revenues_04438122-c607-4c53-bb41-2e3864c06479.pdf | `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/JAY/financial_performance/2023-04-11_q3fy23-update-march-record-trips-and-revenues_04438122-c607-4c53-bb41-2e3864c06479.pdf` | unknown_document | `validation_gate:insufficient_metrics:0` | insufficient metrics, document-family policy gap | safe fail; Q3 update produced zero canonical metrics and may be a policy-gap noncandidate |
| MQR | `7e6d1ae5-51be-4828-907c-d2aa3f8528e7` | 2025-07-28_results-of-meeting_7e6d1ae5-51be-4828-907c-d2aa3f8528e7.pdf | `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/asx/docs/MQR/financial_performance/2025-07-28_results-of-meeting_7e6d1ae5-51be-4828-907c-d2aa3f8528e7.pdf` | DATA_MISSING | `classifier_low_confidence:0.0` | classifier evidence missing, document-family policy gap | safe fail but not expected before repair; results-of-meeting should be classified as meeting/proxy material |

## Bucket Counts

```json
{
  "classifier evidence missing": 1,
  "document-family policy gap": 3,
  "eligible report with missing scale evidence": 2,
  "eligible report with scale validation issue": 2,
  "insufficient metrics": 1,
  "parser/table coverage gap": 2,
  "period/source mismatch": 3,
  "true noncandidate": 6
}
```

## Repeated Root Causes

1. Candidate-selection and document-family policy gaps: six known noncandidates failed closed, MQR missed a results-of-meeting noncandidate pattern, and NIC/JAY remain exact-policy audit candidates.
2. Source-bound scale evidence gaps: WHC, AZJ, EDU, and NIC failed `scale_unknown`; AZJ/EDU had extracted metrics but no accepted scale proof.
3. Existing truth gates are working: HUB/LBL announcement-date period-end, DXC net operating income as EBIT, and CTN period-source mismatch all failed closed.

## Fix Made

Implemented one narrow source-bound fix: exact title-level `results of meeting` detection now maps to existing `meeting_or_proxy_notice` noncandidate handling. This addresses MQR `7e6d1ae5-51be-4828-907c-d2aa3f8528e7` without loosening any validation gate.

Files changed:

- `financial-engine_v2/backend/app/services/multipass_extraction.py`
- `financial-engine_v2/backend/tests/test_multipass_extraction.py`

## Count-24 / Count-32 Decision

- Count-24 rerun later: not justified now from this single-document policy repair; audit the scale family first.
- Count-32: remains blocked and requires a separate approval packet.

## DATA_MISSING

- No direct source-PDF text inspection was performed in this audit; source paths and classifications come from count-24 artifacts.
- Accepted-output row refs/extraction_run_id remain DATA_MISSING from the count-24 accepted-output audit.
- NIC and JAY need exact source-text review before any document-family exclusion is added.

## Validation

- JSON validation: all 6 new JSON artifacts and all 11 bounded-validation JSON artifacts parsed successfully.
- Focused pytest: `8 passed` for `test_source_document_classifier_excludes_known_false_positive_classes`.
- `py_compile`: passed for the touched classifier and test files.
- `ruff`: passed for the touched classifier and test files.
- `git diff --check`: passed.
- `git diff --cached --check`: passed.
- Task card validate/check-diff: passed.
- Registry read-only list-active: passed with `active_jobs=[]`.
- Source PDF staged/worktree checks: no PDF paths reported.
- Explicitly not run: count-24 sample rerun, count-32, broad extraction, backfill.

## Unsafe Actions Avoided

- count-24 rerun not run
- count-32 not run
- broad extraction/backfill not run
- DB/Qdrant/news/memory mutation not run
- source PDF edits not run
- prompt/gold-label/runtime/schema changes not run

## Next Exact Repair Prompt

Audit the remaining count-24 `scale_unknown` failures only: WHC, AZJ, EDU, and NIC. Do not rerun samples. Inspect source text/table headers for source-bound scale evidence and implement at most one narrow tested scale-evidence repair if supported.
