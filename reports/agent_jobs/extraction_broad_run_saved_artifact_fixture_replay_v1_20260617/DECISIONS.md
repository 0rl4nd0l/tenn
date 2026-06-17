# Decisions

## D1: Use LBL Saved Artifact

Decision: `accepted`

Reason: `reports/agent_jobs/extraction_lbl_income_row_ref_repair_v1_20260616/lbl_replay_summary.json` already contains real saved extraction fields needed for the output contract: `metrics`, `row_refs`, `field_provenance`, `metric_source_scales`, `metric_scale_sources`, `scale_validation`, `status`, ticker, document id, and source provenance.

## D2: Do Not Run Extraction

Decision: `accepted`

Reason: the owner requested a bounded no-canonical-write fixture/replay. Transforming the saved artifact through the current broad-run helper contract validates the record shape without runtime/data risk.

## D3: No Source Code Changes

Decision: `accepted`

Reason: the prior local commit already added the broad-run fields. This slice only validates that contract on one existing saved artifact.

## D4: Treat Empty Risk Flags As Valid For This Fixture

Decision: `accepted`

Reason: the LBL saved artifact has complete provenance for all seven non-null metrics and no scale/magnitude review flags under the generic report-only rules. That proves the field is present and machine-readable, but does not exercise a positive risk case.
