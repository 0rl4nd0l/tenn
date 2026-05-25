# Real Signal Scorecard Manifest

Job: `real_signal_scorecard_manifest_v1`
GitHub issue: #70
Lane: Evaluation
Execution mode: SAFE EXTENSION, report-local only
Branch: `audit/repo-hygiene-safe-audits-v1-20260525`
Base evidence commit: `cb87a77395e956710969494a6cfe5e0fd19e501e`

## Decision

The safe extension is complete as a report-local manifest slice. It creates a
machine-readable `real_signal_readiness_v1` scorecard contract from existing #54
audit metadata and current repo evidence. It does not add product/runtime code
and does not enable a Cockpit-visible Real Signal scorecard.

## What Was Added

- `manifest.json`: evaluation-spine-style manifest metadata for the report-local
  Real Signal scorecard slice.
- `scorecards.json`: explicit mapping rows for Real Signal readiness outcomes,
  including `ACTIONABLE_SIGNAL`, `INSPECTABLE_CONTEXT`, `WEAK_CONTEXT`,
  `DATA_MISSING`, `UNSUPPORTED_OR_NOT_VERIFIED`, `DEGRADED_RUNTIME`, and
  `REVIEW_ONLY`.
- `status.json`, `validation.json`, and `diff-check.json`: closeout and
  validation evidence.

## Scorecard Contract

Every scorecard row uses:

- `scorecard_profile: real_signal_readiness_v1`
- explicit `outcome_class`
- explicit `input_surface`
- explicit `required_metadata`
- explicit `hard_stops`
- explicit `do_not_overclaim`

The rows intentionally prevent these unsafe shortcuts:

- LLM/model confidence cannot create `claim_verified`.
- Retrieval score cannot create `claim_verified`.
- Memory signal confidence/materiality cannot become financial truth.
- News `SOURCE_READY` means inspectable context only.
- `unknown_unclassified` and snippet-only sources cannot verify claims.
- Missing canonical rows or generated extracted-payload artifacts must stay
  `DATA_MISSING`.

## Confirmed

- Source artifacts are the #54 report bundle:
  `reports/agent_jobs/real_signal_calibrated_scorecard_v1_20260524/README.md`,
  `scorecard_proposal.json`, and `gap_register.json`.
- The manifest and scorecards are report-local artifacts only.
- No backend, frontend, runtime, parser, extraction, prompt, gold-label,
  source-label semantic, DB/Qdrant/news/memory, model, or service config file
  changed.

## DATA_MISSING

- No product Real Signal runtime implementation exists in this branch.
- No Cockpit-visible Real Signal UI was implemented or validated.
- No current generated extracted-payload artifact set exists for confirmed
  metric payload scoring.
- No live runtime or data-store state was sampled for this report-local slice.

## Validation

- Task-card validate: passed.
- Registry list-active before claim: passed with `active_jobs: []`.
- Registry check-overlap: passed.
- Registry claim/release: passed.
- JSON validation for `manifest.json`, `scorecards.json`, `status.json`,
  `validation.json`, and `diff-check.json`: passed.
- Content checks for `scorecard_profile: real_signal_readiness_v1`: passed.
- `git diff --check` and `git diff --cached --check`: passed.
- Task-card `check-diff`: passed.

## Next Step

No child issue is required from this report-local slice. Any future product
implementation should be a separate reviewed task because Cockpit-visible
display would touch product surfaces and raise collision risk.
