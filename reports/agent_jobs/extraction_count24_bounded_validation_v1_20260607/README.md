# Count-24 Bounded Extraction Validation

Generated: 2026-06-07T07:36:07.155327Z

State: `completed_bounded_count24_validation`.

Scope: exactly one bounded count-24 validation target on canonical
`bfe3a77ec6692d5052eefec7454461e75459f7e3`. No count-32, no broad extraction, no backfill, and no full
ticker-universe extraction.

## Result

- sample_completed: True
- ok: 8
- ok_low_confidence: 0
- failed: 16
- exceptions: 0
- failure_taxonomy: `{"classifier_low_confidence:0.0": 1, "source_noncandidate:board_change_notice": 1, "source_noncandidate:meeting_or_proxy_notice": 2, "source_noncandidate:operational_project_update": 1, "source_noncandidate:pre_results_segment_re_presentation": 1, "source_noncandidate:share_sale_or_gross_proceeds_announcement": 1, "validation_gate:announcement_date_period_end": 2, "validation_gate:insufficient_metrics": 1, "validation_gate:metric_label_mismatch": 1, "validation_gate:period_source_mismatch": 1, "validation_gate:scale_unknown": 4}`
- low_confidence_taxonomy: `{}`
- count24_verdict: `COUNT24_FAILED_LOW_ACCEPTED_COUNT`
- count32_decision: `blocked; count-32 requires a separate approval packet`

## Selected Document Manifest

- seed: 20260602
- requested_count: 24
- actual_count: 24
- candidate_pool_count: 28633
- candidate_pool_ordered_sha256: `3d99f44885fd056ac3f112d56abe95d14dd1ac9affdcd7315f860f690cdeb63f`
- candidate_pool_sorted_sha256: `e4d57b2cdb3e8583a3aeaf33fba5a2d959383500733473349771f80531629e7a`
- first16_overlap_with_post_pr301_count16: 16
- first16_exact_order_match: True
- selected_document_ids_sha256: `7108699e7d338ea2635153e0acfc3ccafebb1cda6b8b03a0c74e5a5271e9ea6c`
- selected_document_ids: `36e172ec-2650-4a9f-9ef0-a4366a3b8d31, 9640d9f1-a45b-492d-8df5-9bad0f46431c, aadead44-11f3-46d5-933b-6f2c8792e6f9, 05a85ffc-25cb-49a7-b770-df5e08f88ed9, e7290bdf-2865-468c-9a9b-9fcc6a61d446, 488d6f1a-0180-4fca-8dcf-c4cdfc0f342e, 0be5515d-6e8b-4c1f-9e20-e5d1ec67acdd, ea1b1f56-702e-4e23-a2fe-36c8136cf99c, bf82c108-980b-4792-ad76-838c3fe446ca, 11e11c93-52f6-444a-9c24-e5d1e41141cf, f8a24788-dbe0-48f7-ad41-654f2c8a3845, a6118b61-77b6-4f13-bd6f-58654455ae9a, 419bcca8-213e-4706-8962-8e3bd8adf091, 551c6b84-1053-405c-a833-4ecc018e2045, f2240712-9dde-41e0-88fa-29c1a0080dab, dec0b5f1-e6d2-48d8-ad9d-16ffd540ee39, 7394ad43-57ec-4edf-a91e-72844307948b, ac3c9ab0-e01a-4996-95f9-6466388ddc9c, 50398d3d-27f7-4d9e-8a26-a2d69f128a1c, 91561659-014b-4c88-865d-a6dec2fd8e35, 5eaa9900-0749-448a-a7bc-a5af19eddb23, 04438122-c607-4c53-bb41-2e3864c06479, 0be9e3e7-70b3-40af-9895-8c0a99fa778e, 7e6d1ae5-51be-4828-907c-d2aa3f8528e7`
- new_documents_positions_17_24: `7394ad43-57ec-4edf-a91e-72844307948b, ac3c9ab0-e01a-4996-95f9-6466388ddc9c, 50398d3d-27f7-4d9e-8a26-a2d69f128a1c, 91561659-014b-4c88-865d-a6dec2fd8e35, 5eaa9900-0749-448a-a7bc-a5af19eddb23, 04438122-c607-4c53-bb41-2e3864c06479, 0be9e3e7-70b3-40af-9895-8c0a99fa778e, 7e6d1ae5-51be-4828-907c-d2aa3f8528e7`


## Accepted-Output Audit

- accepted_count: 8
- unsafe_accepted_output_count: 0
- data_missing_count: 8
- HUB/LBL-like half-year guard unsafe IDs: ``


## Side-Effect Audit

- DB files changed: False
- Qdrant changed: False
- Risk-note mutated: False
- News route used: False
- Memory mutated: False
- Source PDFs changed: False
- Queues clean after run: True

## DATA_MISSING / Blockers

- 36e172ec-2650-4a9f-9ef0-a4366a3b8d31: row refs/extraction_run_id
- 0be5515d-6e8b-4c1f-9e20-e5d1ec67acdd: row refs/extraction_run_id
- 11e11c93-52f6-444a-9c24-e5d1e41141cf: row refs/extraction_run_id
- a6118b61-77b6-4f13-bd6f-58654455ae9a: row refs/extraction_run_id
- f2240712-9dde-41e0-88fa-29c1a0080dab: row refs/extraction_run_id
- 7394ad43-57ec-4edf-a91e-72844307948b: row refs/extraction_run_id
- 91561659-014b-4c88-865d-a6dec2fd8e35: row refs/extraction_run_id
- 0be9e3e7-70b3-40af-9895-8c0a99fa778e: row refs/extraction_run_id

## Unsafe Actions Avoided

- count-32 not run
- broad extraction not run
- backfill not run
- full ticker-universe extraction not run
- DB/Qdrant/news/memory/source-PDF/prompt/gold-label/runtime/schema/model/GPU mutation not run

## Next Recommended Prompt

Review the count-24 accepted-output audit and failure taxonomy; create a separate approval packet before any count-32 or containment mutation.
