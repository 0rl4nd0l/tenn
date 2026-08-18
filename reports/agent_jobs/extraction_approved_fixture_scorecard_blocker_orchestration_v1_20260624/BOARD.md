# Review Board

## Evidence Inspected

- Git guard preflight: clean task branch, no active registry jobs, PR #405 clean
  and green before continuation.
- Issue #97 current body and definition of done.
- Current replay/scorecard artifacts from
  `extraction_approved_15_fixture_replay_scorecard_v1_20260623`.
- Current hard-failure rows in `failure_rows.json`.
- Source PDF text for BHP, MIN, QBE, EQR, and GRE via resolved
  `source_resolution.json` paths.
- Evidence-only worker outputs for scored failures and fail-closed fixtures.
  Both workers produced useful evidence but failed bridge schema validation
  because `stop_condition_hit` was rendered as `false` instead of `no`; Codex
  did not treat them as final decisions.

## Perspectives

### Architect

Finding: The hard scored failures cluster into existing extractor classes:
formal income-statement row recovery, Appendix 5B section-total selection,
cash-flow cash-end row aliases, tiny PP&E capex, and share-count column
selection. These can be fixed inside `multipass_extraction.py` without schema,
prompt, gold-label, or DB mutation.

Risk: Each class-level heuristic can affect more than one document. The edits
must be deterministic, row-label constrained, and covered by negative tests.

Recommended action: Proceed with narrow deterministic helpers and focused
regressions.

### Skeptic / Red Team

Finding: The largest count, `ambiguous_quarantined=73`, is not evidence of
parser failure. It is a candidate-review/gold-policy blocker. Treating those
rows as code failures would silently promote unapproved expectations.

Risk: DXS and ANZ fail-closed cases involve sector/entity-specific scale and
ratio gates. They are not yet safe targets for a broad fix.

Recommended action: Fix only rows with exact source evidence and keep
candidate-review/ambiguous rows quarantined.

### Product / Value

Finding: The best production-readiness value is reducing hard scored failures:
4 missing metrics and 4 wrong values. These are visible correctness errors in
accepted payloads. Fixing them improves the scorecard without changing policy.

Risk: A report-only board without implementation would not move #97 forward.

Recommended action: Proceed with the class-level hard-failure fix set.

### Validation / Test

Finding: Denominator is unchanged: 146 metric expectations, 73 scored, 73
quarantined. Current blocker counts are `missing_expected_metric=4`,
`present_wrong_value=4`, `not_evaluated_no_actual_payload=16`, and
`ambiguous_quarantined=73`.

Required proof: focused tests for every deterministic helper, full
`test_multipass_extraction.py`, and an approved 15-fixture no-write replay and
#97 scorecard after fixes.

Recommended action: Proceed, but call final status `PARTIAL` unless the
scorecard gate passes.

### Repo Hygiene / Git Guard

Finding: Branch `safe/extraction-approved-15-fixture-replay-scorecard-v1-20260623`
is the active PR #405 branch. Guard preflight found no active duplicate job and
no dirty state at task start. A continuation task card validates.

Risk: Report artifacts under `reports/` are ignored and must be force-added if
committed. Do not add stale prior board/worker artifacts from the earlier
report directory.

Recommended action: Continue on PR #405 branch with exact task-card allowlist.

### Domain Expert

Finding: Source-proven rows:

- BHP page 44: `Attributable to BHP shareholders = 11,304`; page 46:
  `Cash and cash equivalents, net of overdrafts, at the end of the financial
  year = 15,246`.
- MIN Appendix 4D page 1: attributable profit `495`; formal income statement
  page 14: `PROFIT/(LOSS) FROM OPERATIONS = 1,031` and `Equity holders of the
  parent = 495`.
- QBE page 17: `Payments for purchase of property, plant and equipment = (9)`;
  page 28: `NUMBER OF SHARES MILLIONS`, `Issued ordinary shares, fully paid at
  30 June = 1,510`, while the adjacent `US$M` amount column is not a share
  count.
- EQR Appendix 5B section 2.6 current quarter: `(2,656)`.
- GRE Appendix 5B section 2.6 current quarter: `(624)`.

Recommended action: Recover only these exact row classes. Do not adjust DXS
stapled-entity scope or ANZ bank revenue-ratio gates in this patch.

### Chair

Decision: proceed.

Rationale: The board found a source-proven, bounded class-level fix path for
all 8 hard scored failures. The same evidence does not justify touching
candidate-review rows, gold labels, DXS entity scope, ANZ sector gates, or
count-24/count-32.

## Zoom-Out Answers

- Real root problem: hard scored extraction misses/wrong values plus
  non-code quarantine policy blockers. This patch targets the hard scored
  extraction failures only.
- Overfitting risk: reduced by class-level helpers and negative tests rather
  than ticker-specific branches.
- Report-only loop: avoided; board proceeds to implementation.
- Broad progress: yes, if hard scored failures fall without worsening accepted
  payload coverage.
- Class-based approach: better than another one-document repair.
- Best next action: implement deterministic row recovery for the source-proven
  hard failures, then rerun full no-write replay and scorecard.
