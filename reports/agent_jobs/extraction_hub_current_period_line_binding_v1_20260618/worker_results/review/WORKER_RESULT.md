# Worker Result

Status: `STALLED_NO_RESULT`

The read-only review worker was dispatched with exactly one allowed write file:
this result file. It did not produce findings within the allotted wait window
and was closed before report closeout to avoid late writes.

No code, tests, task cards, GitHub state, extraction, runtime, data store,
source PDF, prompt, gold label, model/GPU/service config, merge, rebase, stash,
clean, or push action was performed by the review worker.

Parent orchestrator performed the final local review gate instead.
