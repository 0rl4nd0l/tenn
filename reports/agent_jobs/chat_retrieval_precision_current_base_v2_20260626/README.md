# Chat Retrieval Precision Current Base V2

Status: `LOCAL_FIX_VALIDATED_READY_TO_PUBLISH`

This task fixes issue #257 from canonical head
`659c5a507aaf9fa03e46021495d8ad998ba8ba46`.

The local diff is limited to the chat quality scorer, its focused regression
tests, the task card, and this report bundle.

Next gate: push PR, wait for GitHub checks, then close issue #257 only after
the merge commit is verified contained in
`origin/migration/clean-runtime-baseline-reconstruct-v1`.
