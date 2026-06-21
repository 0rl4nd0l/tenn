# Decisions

## Proceed On Continuation Branch

Decision: create and use
`safe/extraction-whc-edu-mixed-unit-failclosed-v1-20260621`.

Reason: the prior local fixture commit was on the already-merged PR #379 branch.
The continuation branch preserves that fixture commit and keeps the product fix
out of the merged PR branch.

## Use Payload-Local Risk Evidence

Decision: implement the fail-closed behavior inside `_validate_gate` using only
payload-local evidence.

Reason: WHC already exposed mixed `metric_source_scales`; EDU did not, but did
expose extreme cash-flow magnitude relative to revenue. Re-parsing source pages
or correcting values would broaden the lane and require a larger provenance
repair.

## Reuse Existing Risk Family

Decision: return
`validation_gate:accepted_output_scale_magnitude_risk:<codes>`.

Reason: saved-artifact broad runs already use this failure family, and the exact
manifest expects these cases to fail closed rather than pass as accepted output.

## No Workers

Decision: no subagents or workers.

Reason: the lane was a two-file validation-gate change with a single exact replay
target. Delegation would add coordination overhead without reducing risk.

## Push Boundary

Decision: push the continuation branch and open one fresh PR only after local
validation, code review, diff checks, and report artifact checks pass.

Reason: the user approved proceeding from the recommended branch/push path, and
the exact no-write replay now passes with `side_effect_pass=true`.
