# Post-PR301 Count-16 Extraction Validation

Generated: 2026-06-07T04:59:13.733719Z

Scope: exactly one bounded count-16 sample on HEAD
`314132710bd6431331053b0be5a4300bea069e23`. No broad extraction, no backfill, no count-24/count-32,
and no full ticker-universe extraction.

## Result

- ok: 7
- ok_low_confidence: 0
- failed: 9
- exception_count: 0
- failure_taxonomy: `{"source_noncandidate:board_change_notice": 1, "source_noncandidate:meeting_or_proxy_notice": 1, "source_noncandidate:operational_project_update": 1, "source_noncandidate:pre_results_segment_re_presentation": 1, "source_noncandidate:share_sale_or_gross_proceeds_announcement": 1, "validation_gate:metric_label_mismatch": 1, "validation_gate:period_source_mismatch": 1, "validation_gate:scale_unknown": 2}`
- low_confidence_taxonomy: `{}`
- unsafe_row_check: `{"negative_revenue": [], "nonpositive_shares": []}`

## Manifest

- seed: 20260602
- candidate_pool_count: 28633
- candidate_pool_ordered_sha256: `3d99f44885fd056ac3f112d56abe95d14dd1ac9affdcd7315f860f690cdeb63f`
- candidate_pool_sorted_sha256: `e4d57b2cdb3e8583a3aeaf33fba5a2d959383500733473349771f80531629e7a`
- selected_document_ids: `36e172ec-2650-4a9f-9ef0-a4366a3b8d31, 9640d9f1-a45b-492d-8df5-9bad0f46431c, aadead44-11f3-46d5-933b-6f2c8792e6f9, 05a85ffc-25cb-49a7-b770-df5e08f88ed9, e7290bdf-2865-468c-9a9b-9fcc6a61d446, 488d6f1a-0180-4fca-8dcf-c4cdfc0f342e, 0be5515d-6e8b-4c1f-9e20-e5d1ec67acdd, ea1b1f56-702e-4e23-a2fe-36c8136cf99c, bf82c108-980b-4792-ad76-838c3fe446ca, 11e11c93-52f6-444a-9c24-e5d1e41141cf, f8a24788-dbe0-48f7-ad41-654f2c8a3845, a6118b61-77b6-4f13-bd6f-58654455ae9a, 419bcca8-213e-4706-8962-8e3bd8adf091, 551c6b84-1053-405c-a833-4ecc018e2045, f2240712-9dde-41e0-88fa-29c1a0080dab, dec0b5f1-e6d2-48d8-ad9d-16ffd540ee39`
- document_class_taxonomy: `{"board_change_notice": 1, "financial_report": 5, "meeting_or_proxy_notice": 1, "operational_project_update": 1, "pre_results_segment_re_presentation": 1, "share_sale_or_gross_proceeds_announcement": 1, "unknown_document": 6}`
- post-PR299 comparability: `FULL_AGAINST_POST_PR299_SAMPLE`

## Side Effects

- DB files changed: False
- Qdrant changed: False
- Queues clean after run: True
- News route used: false
- Memory mutated: false
- Source PDFs changed: False

## Runtime Notes

- The runner used the existing PyMuPDF fallback for every document because
  Docling import failed with `No module named 'transformers'`.
- DXC failed closed with
  `validation_gate:metric_label_mismatch:ebit:net_operating_income`.
- LBL remained accepted and is carried into the Milestone 4 accepted-output
  taxonomy as a suspicious accepted row.

## Count-24 Decision

Count-24 is not authorized by this report. See `status.json` for the
recommendation reason.

## DATA_MISSING

- Reliable GPU memory telemetry: nvidia-smi failed.
