# PR Review

Decision: `pass_with_risk`

## Findings

No blocking findings.

## Scope Reviewed

- `financial-engine_v2/scripts/broad_extraction_test.py`
- `financial-engine_v2/scripts/test_broad_extraction_test.py`
- task cards and report bundles for:
  - `extraction_broad_run_provenance_risk_flags_v1_20260617`
  - `extraction_broad_run_saved_artifact_fixture_replay_v1_20260617`
  - `extraction_broad_run_positive_risk_fixture_v1_20260617`

## Review Notes

- The source diff surfaces row-level metric provenance into broad-run records
  and adds machine-readable accepted-output scale/magnitude risk flags.
- Summary rollups now include provenance coverage and risk flag distribution.
- Focused unit tests cover provenance audit construction, risk flag shape, and
  summary rollups.
- Report fixtures cover one saved accepted LBL output and one exact positive
  synthetic risk case.
- The branch does not mutate canonical data or runtime state.

## Residual Risk

- Saved and synthetic fixtures are not substitutes for a future approved broad
  extraction run.
- The local task cards do not authorize push or PR creation.
- Live ledger remains `DATA_MISSING`, with fallback search clean for this exact
  branch/topic.

## Recommendation

Ready for owner-approved push and PR creation from branch
`safe/extraction-broad-run-provenance-risk-flags-v1-20260617`.
