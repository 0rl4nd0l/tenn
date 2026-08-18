# C01 Decision Record

## Decision

C01 is reconciled by a safe-extension docs/test contract fix. The accepted backend contract is:

- SQLite is forbidden for canonical financial truth, vector storage, embedding caches of record, and hidden Qdrant retrieval fallback.
- SQLite is allowed for explicitly documented qualitative memory, operational state, feedback, marketplace-operational, and workspace/news projection stores.
- `uuid4` is forbidden for vector IDs, chunk IDs, canonical financial IDs, canonical artifacts, and reproducibility keys.
- `uuid4` is allowed for operational task/session/job/report/feedback/proposal/event IDs and document primary-key insertion when those IDs are not used as vector/canonical/reproducibility IDs.
- Logical vector IDs remain deterministic `document_id:chunk_index`.

## Why This Is Not A Bandaid

The failing tests were not simply relaxed:

- The SQLite invariant still scans backend runtime files and fails any `sqlite3` import outside exact documented exception paths.
- The UUID invariant now performs AST checks instead of checking broad `co_names`; it still fails future unapproved `uuid4` calls, including any new `uuid4` call in `process_document` outside the exact operational run-id fallback.
- The vector-ID tests now exercise the active embedding-stage function that constructs upsert points. The old tests disabled extraction and then expected `process_document` to upsert Qdrant points, which no longer matched the active extraction-gated control flow.
- Architecture docs were clarified before relying on the refined tests, so the tests now encode a written contract rather than an undocumented allowlist.

## What Future Agents Must Not Undo

- Do not restore a blanket backend `sqlite3` ban that breaks documented memory and operational stores without first approving a real migration away from those stores.
- Do not treat documented SQLite exceptions as approval to use SQLite for canonical financial truth, vector storage, embedding caches, or hidden retrieval fallback.
- Do not replace deterministic logical vector IDs with random UUIDs.
- Do not use the allowed operational UUID list as permission to add new random IDs without checking whether the ID becomes canonical, vector, chunk, or reproducibility state.
- Do not treat `financial-engine_v2/worker/app/tasks.py` random vector UUID usage as fixed by this task; it remains a separate legacy-worker follow-up.

## DATA_MISSING

- Whether a same-shape base CI run would prove C01 inherited versus newly exposed.
- Whether GitHub PR #39 would pass C01 after applying these local changes and rerunning CI.
- Final policy for physical Qdrant point IDs when `embeddings.py` maps logical string IDs to deterministic UUIDv5 IDs in local mode.
