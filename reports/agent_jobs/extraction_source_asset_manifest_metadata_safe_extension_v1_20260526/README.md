# Extraction Source Asset Manifest Metadata Safe Extension

Job: `extraction_source_asset_manifest_metadata_safe_extension_v1_20260526`
Related issue: #99
Lane: Provenance
Supporting lanes: Evaluation, Financial Truth
Mode: SAFE EXTENSION, metadata/report-local/test-only

## Session

- Worktree: `/home/l4nd0/tenn-extraction-source-asset-manifest-metadata-safe-extension-v1-20260526`
- Branch: `safe/extraction-source-asset-manifest-metadata-safe-extension-v1-20260526`
- Base HEAD: `3725591cf76ec1a56428a476e23dbd1ebc4050fc`
- Task card: `docs/agent_tasks/extraction_source_asset_manifest_metadata_safe_extension_v1_20260526.md`
- Registry: shared claim and release succeeded after moving to an isolated worktree.
- Baseline checkout note: initial overlap check in `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` failed only because two pre-existing untracked GitHub task cards were outside this job allowlist. No active registry jobs overlapped.

## What Changed

- Added metadata-only source asset resolver helpers to `extraction_gold_eval_scorecard.py`.
- Added a tracked manifest at `financial-engine_v2/backend/tests/eval_source_assets/confirmed_metric_coverage_source_assets.json`.
- Added focused synthetic tests for manifest load, missing/present source state, hash/size verification, metadata mismatch, path safety, and the rule that source openability does not count as metric correctness.
- Generated `source_asset_resolution_sample.json` under this report directory.

## Manifest Contract

The manifest contains 30 assets: 15 real-gold source assets and 15 confirmed metric coverage source assets. Each entry records `asset_id`, `ticker`, `document_id`, `fixture_id`, expected filename/logical source name, `sha256`, `size_bytes`, `source_kind`, `local_candidate_paths`, `reviewability_status`, `missing_reason`, and notes.

Raw PDFs are not included. The default manifest does not require raw PDFs in CI and does not treat source availability as a metric score.

## Resolver Contract

The resolver loads the manifest, validates candidate paths, checks local file existence under declared source roots, verifies size/hash metadata when expected values are present, and reports `present_verified`, `present_unverified`, `present_metadata_mismatch`, `missing`, or `manifest_error`.

The generated sample resolved all 30 assets through the local `/data/asx/docs` candidate root and reported them as `present_unverified` because the committed manifest does not carry expected hashes.

## Confirmed

- #99 now has a durable, tracked metadata-only manifest and executable resolver foundation.
- Raw source PDFs were not committed, moved, deleted, copied, or modified.
- Source openability/reviewability is explicitly separate from extraction correctness.
- The resolver reports local source state without writing DB, Qdrant, news, memory, canonical financial truth, labels, prompts, parser routing, runtime config, or service state.
- #97 extracted-payload scoring remains a separate correctness layer.
- #98 metric contract parity remains a separate metric-family support guard.

## Inferred

- This is the correct safe next step before broader real-gold payload scoring because it makes source asset reviewability testable without changing extraction behavior.
- The manifest can be extended with expected SHA256 values after a separately approved source asset hash capture step.

## Speculative

- If CI gets a mounted `/data/asx/docs`, the same resolver can emit present states there; default CI should still pass when that root is absent.

## DATA_MISSING

- Expected SHA256 hashes for the 30 source PDFs are not committed in this manifest.
- Current-turn source route/openability through the live backend was not exercised.
- Approved actual extracted payloads for all confirmed metric coverage expectations are still missing.
- Approved broad accuracy thresholds for confirmed metric coverage remain missing.
- Expanded metric-family policy for persisted-only or planned fields from #98 remains incomplete.
- `.cursor/rules/*` and `graphify-out/GRAPH_REPORT.md` were absent in this isolated checkout.

## #97 / #98 / #99 Interaction

#99 is advanced by adding the source asset manifest/resolver foundation. #97 can continue to score extracted payload correctness from supplied actual payloads, but source asset presence does not affect metric correctness. #98 continues to gate whether a metric family is scoreable before broader payload scorecards include expanded fields.

## Remaining Blockers

- Real-gold extracted-payload scoring cannot be trusted broadly until approved actual payloads, thresholds, source asset hashes or equivalent review metadata, and #98 metric-family policy are all in place.
- #96 broad backfill remains blocked; this task adds reviewability metadata only and does not authorize production extraction, backfill, canonical truth writes, or datastore mutation.

## Validation

- Task card validate: PASS.
- Registry list-active: PASS; no active jobs before isolated claim.
- Registry check-overlap: PASS in isolated worktree.
- Registry claim: PASS.
- Registry release: PASS.
- Py compile: PASS.
- Focused pytest: PASS, `10 passed, 1 warning in 0.13s`.
- Ruff: PASS.
- Manifest JSON validation: PASS.
- Resolution artifact JSON validation: PASS.
- `git diff --check`: PASS.
- Raw PDF staging check: PASS, no `.pdf` paths in `git status --short --untracked-files=all`.
- Task-card `check-diff`: PASS, no disallowed files.

## Generated Artifacts

- `reports/agent_jobs/extraction_source_asset_manifest_metadata_safe_extension_v1_20260526/source_asset_resolution_sample.json`
- `reports/agent_jobs/extraction_source_asset_manifest_metadata_safe_extension_v1_20260526/status.json`
- `reports/agent_jobs/extraction_source_asset_manifest_metadata_safe_extension_v1_20260526/validation.json`
- `reports/agent_jobs/extraction_source_asset_manifest_metadata_safe_extension_v1_20260526/diff-check.json`

## Project Memory Recommendation

Save a memory note after closeout: #99 now has a tracked metadata-only source asset manifest and resolver in `extraction_gold_eval_scorecard.py`; 30 real-gold/confirmed-coverage source assets are manifest-bound, source openability remains reviewability-only, and broad payload scoring still needs approved actual payloads, #98 policy, source hashes/review metadata, and thresholds.
