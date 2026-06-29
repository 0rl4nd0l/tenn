# Lane E - Ambiguous Quarantined Grouping

Status: PARK_POLICY_EVIDENCE_REVIEW

## Source Evidence

- Post-PR #461 scorecard has `ambiguous_quarantined=73`.
- Blocking examples include ANZ, AZJ, CSL, DXS net debt, FMG, QBE net debt, SEG
  net debt, TCL, TLS, and WOW rows.

## Failure Lineage

- The current scoring policy quarantines expectations that require review or
  have ambiguous label evidence.
- These rows are not equivalent to extractor misses. Several have actual
  context but are still quarantined because the source evidence or label
  support is not promotable under the current #97 policy.
- Read-only scout split the 73 rows into 70 `candidate_review_required` rows
  and 3 `ambiguous_label` net-debt rows. By family: core 38, cash-flow 28,
  capital-structure 7.

## Remediation Eligibility

Final classification: `NOT_EXTRACTOR_ELIGIBLE`.

This lane is grouping/reporting work unless the worker finds a deterministic
subclass that is already source-confirmed and blocked only by stale grouping.
Changing labels, scorecard policy, gold evidence, or ambiguity semantics is
forbidden without explicit approval.

## Validation Plan

- Produce deterministic grouping by fixture, metric family, and support status.
- No code change unless a separate owner-approved scorecard policy task exists.

## Next Action

Route to human/source evidence and net-debt policy review. No extractor change
is justified from Lane E evidence alone.
