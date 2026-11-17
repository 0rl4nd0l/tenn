# Real-Gold Review Asset Bundle

Job: `real_gold_review_asset_bundle_v1_20260526`
Related issue: #99
Lane: Provenance
Mode: SAFE EXTENSION, metadata/report-only

## What Changed

- Added a committed metadata-only real-gold review manifest with fixture/source bindings, file sizes, and SHA256 hashes.
- Generated a report-local resolver artifact proving the current host can verify all real-gold source PDF identities.
- Documented clean-checkout placement for an explicitly approved off-git raw-PDF bundle.
- Recorded that no raw-PDF bundle was created because no approval was provided.

## Current Host Resolution

- Total real-gold assets: `15`
- Present and hash/size verified: `15`
- Missing: `0`
- Metadata mismatch: `0`

## Boundaries

Raw PDFs were not committed, copied into git, modified, or bundled. This work records reviewability metadata only; it does not mutate extraction behavior, labels, DB, Qdrant, news, memory, model, runtime, GPU, services, or canonical financial truth.

## Artifacts

- `financial-engine_v2/backend/tests/eval_source_assets/real_gold_review_source_assets.json`
- `reports/agent_jobs/real_gold_review_asset_bundle_v1_20260526/real_gold_source_asset_manifest.json`
- `reports/agent_jobs/real_gold_review_asset_bundle_v1_20260526/source_asset_resolution.json`
- `reports/agent_jobs/real_gold_review_asset_bundle_v1_20260526/placement_runbook.md`
- `reports/agent_jobs/real_gold_review_asset_bundle_v1_20260526/off_git_bundle_status.json`
