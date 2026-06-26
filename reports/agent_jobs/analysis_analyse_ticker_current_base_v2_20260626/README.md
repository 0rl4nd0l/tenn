# Analyse Ticker Current Base V2

Status: `LOCAL_FIX_VALIDATED_READY_TO_PUBLISH`

This task fixes issue #253 from canonical head
`69980b4412ab96808d1134cd14aaf47462a90560`.

The local diff is limited to the documented `analyse_ticker()` entrypoint, its
focused regression test, the task card, and this report bundle.

Next gate: push PR, wait for GitHub checks, then close issue #253 only after
the merge commit is verified contained in
`origin/migration/clean-runtime-baseline-reconstruct-v1`.
