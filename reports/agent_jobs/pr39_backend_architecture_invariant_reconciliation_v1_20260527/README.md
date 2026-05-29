# PR #39 C01 Backend Architecture Invariant Reconciliation

## Status

- Job: `pr39_backend_architecture_invariant_reconciliation_v1_20260527`
- Issue: #105 remains open.
- PR: #39 remains open, draft, unmerged, and not merge-ready.
- Cluster: C01 only.
- Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- Branch: `migration/clean-runtime-baseline-reconstruct-v1`
- Local HEAD: `06cb29067d1021ea89d7b93341653d5750babe92`
- GitHub PR head inspected: `8635833b7d7359ed55daf0495eb49c5457bab91d`
- Preservation commit: `8c9e3e0a9fd16034dee47317d7b69e80704c5453` is contained by local HEAD.

## Scope Summary

C01 covers backend architecture invariant failures around:

- broad `sqlite3` import bans;
- random `uuid4` usage;
- deterministic vector IDs;
- stale vector-ID tests that did not exercise the active embedding-stage path.

No C02-C13 fixes were implemented.

## Preflight

- `pwd -P`: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- `git rev-parse --show-toplevel`: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- Branch: `migration/clean-runtime-baseline-reconstruct-v1`
- HEAD: `06cb29067d1021ea89d7b93341653d5750babe92`
- Recent commits:
  - `06cb2906 milestone(extraction): make parser cache source-read-only safe`
  - `8c9e3e0a milestone(repo-hygiene): preserve pr39 ci audit artifacts`
  - `c275e3c8 milestone(news): standardize news artifact paths`
  - `730eb0d8 milestone(news): repair nightly sync ollama url resolution`
  - `e45ae517 chore(repo-hygiene): release restart route audit job`
- `origin/migration/clean-runtime-baseline-reconstruct-v1`: `8635833b7d7359ed55daf0495eb49c5457bab91d`
- PR #39 GitHub status: open, draft, base `migration/clean-runtime-baseline-reconstruct-base-36130cbd`, head ref `migration/clean-runtime-baseline-reconstruct-v1`.
- PR #39 check rollup still shows `lint-and-test` failed for run `26439822448`; `scan` passed.
- `.cursor/rules` files: absent in this checkout, so architecture docs and mirrored tests are the effective local contract.

Unrelated dirty file present before/through this job and not touched:

- `docs/agent_tasks/extraction_primary_canary_retry_after_cache_fix_v1_20260527.md`

## Registry

- `python3 scripts/agent_job_registry.py list-active --read-only`: ok, no active jobs.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/pr39_backend_architecture_invariant_reconciliation_v1_20260527.md`: failed because the unrelated task card above is dirty outside this task allowlist.
- Registry claim: not attempted because `check-overlap` was not safe.
- Registry release: not applicable.

## Exact C01 Failures Inspected

Current GitHub evidence remains run `26439822448` at PR head `8635833b7d7359ed55daf0495eb49c5457bab91d`.

The preserved cluster and live run log both identify these six C01 failures:

- `financial-engine_v2/backend/tests/test_architecture_invariants.py::test_no_sqlite_usage_in_backend_runtime`
- `financial-engine_v2/backend/tests/test_architecture_invariants.py::test_no_uuid4_usage_inside_process_document`
- `financial-engine_v2/backend/tests/test_architecture_invariants.py::test_vector_ids_use_document_id_and_chunk_index`
- `financial-engine_v2/backend/tests/test_architecture_invariants.py::test_process_document_integration_vector_id_and_payload`
- `financial-engine_v2/backend/tests/test_cursor_rule_compliance.py::test_no_sqlite3_in_runtime`
- `financial-engine_v2/backend/tests/test_cursor_rule_compliance.py::test_no_random_uuid_generation_in_pipeline`

Focused local reproduction before remediation:

- `6 failed, 7 passed` for the two invariant test files.

Focused local validation after remediation:

- `13 passed` for the same two invariant test files.

## Architecture-Contract Findings

- The broad SQLite ban was stale/over-broad. `docs/architecture/22_memory_ownership_map.md` intentionally documents SQLite-backed qualitative memory and operational stores.
- SQLite remains forbidden as canonical financial truth, vector store, embedding cache of record, or hidden Qdrant fallback.
- `docs/architecture/SYSTEM_CONTRACT.md` and `docs/architecture/06_embeddings_and_vector_store.md` support deterministic vector IDs as `document_id:chunk_index`.
- Random `uuid4` is forbidden for vector IDs, chunk IDs, canonical financial IDs, canonical artifacts, and reproducibility keys.
- Random `uuid4` remains acceptable for operational task/session/job/feedback/proposal/event IDs and for document primary-key insertion when those IDs are not used as vector/canonical/reproducibility IDs.
- `.cursor/rules` is absent, so the cursor-rule compliance test had to reference the repo architecture docs instead of a missing Cursor rule file.

## Code-Surface Findings

SQLite imports found in backend runtime are documented exceptions:

- qualitative memory stores: `company_memory.py`, `market_memory.py`, `user_thesis_memory.py`;
- operational stores: `ops_store.py`, `response_feedback.py`, `marketplace_price_intelligence.py`, `routes/cockpit_api.py`;
- context lookup over documented memory stores: `api/context.py`.

`uuid4` uses found in backend runtime are operational/document-primary-key exceptions after classification:

- document primary keys: `pipeline.py::insert_discovered_documents`;
- operational run/task/job/session/report IDs: `pipeline.py::process_document`, `api/routes.py::process_single_document`, `eval_task_registry.py::register`, `job_tracker.py::create_job`, `routes/cockpit_api.py` launcher/session functions;
- operational memory/feedback/marketplace IDs: `ops_store.py`, `response_feedback.py`, `memory_events.py`, `user_thesis_memory.py`, marketplace services, `cockpit_service.py`, `router_state.py`.

Vector-ID surface:

- Active backend embedding stage builds logical point IDs as `document_id:chunk_index` in `financial-engine_v2/backend/app/services/pipeline_stages.py`.
- `financial-engine_v2/backend/app/services/embeddings.py` may coerce string point IDs to deterministic UUIDv5 before Qdrant local-mode upsert. That appears deterministic, but the physical-vs-logical point-ID contract remains a documented follow-up because the C01 test now asserts the logical pre-upsert contract.
- `financial-engine_v2/worker/app/tasks.py` contains a legacy/deprecated random vector UUID path. It is outside the backend-app C01 tests and marked out of scope here; future legacy-worker cleanup must not treat this C01 fix as approval to run that worker path.

## Decision

Classification: safe-extension docs/test contract fix.

C01 was not a request to remove every `sqlite3` import. The correct reconciliation is to preserve the backend safety invariant while encoding documented exceptions:

- broadened docs now state exactly where SQLite is allowed and forbidden;
- invariant tests now fail only for SQLite imports outside documented exception files;
- uuid invariant tests now reject `uuid4` for vector/chunk/canonical/reproducibility IDs while allowing exact operational/document-primary-key contexts;
- vector tests now target `run_embedding_stage`, the active embedding path that creates logical vector IDs, instead of disabling extraction and expecting `process_document` to upsert points anyway.

No production code, runtime config, parser routing, prompts, gold labels, Qdrant, DB, news, or memory stores were mutated.

## Files Changed

- `docs/agent_tasks/pr39_backend_architecture_invariant_reconciliation_v1_20260527.md`
- `docs/architecture/06_embeddings_and_vector_store.md`
- `docs/architecture/22_memory_ownership_map.md`
- `financial-engine_v2/backend/tests/test_architecture_invariants.py`
- `financial-engine_v2/backend/tests/test_cursor_rule_compliance.py`
- report files under `reports/agent_jobs/pr39_backend_architecture_invariant_reconciliation_v1_20260527/`

No commit was created because registry overlap/check-diff is blocked by unrelated dirty work outside this task allowlist.

Report-local parking recommendation: after the unrelated dirty task card is
resolved by its owner, stage only the files listed above plus this report
bundle and commit with `fix(evaluation): reconcile pr39 backend architecture
invariants`.

## Validation Results

Passed:

- task-card validate;
- focused local reproduction after remediation: `13 passed`;
- targeted `ruff check`;
- targeted `ruff format --check`;
- `git diff --check`;
- JSON parse validation for report JSON files.

Partial/blocking:

- registry `check-overlap` and task-card `check-diff` are blocked by the unrelated dirty task card `docs/agent_tasks/extraction_primary_canary_retry_after_cache_fix_v1_20260527.md`.

## PR #39 Readiness Impact

C01 is reconciled in this local worktree and has focused passing validation. PR #39 remains not merge-ready because:

- these changes were not pushed or applied to GitHub PR head;
- PR #39 still has failed CI run `26439822448`;
- C02-C13 remain out of scope and unresolved here;
- #105 remains open.

## Next Safe Task

Next recommended cluster: C02, the Cockpit chat/session `llm_client` contract drift, unless the operator prefers to finish a PR-head update/rerun plan for C01 first.

## DATA_MISSING

- Same-shape base CI run proving whether C01 was inherited from base versus newly exposed by PR #39 CI dependency changes.
- Fresh GitHub CI run after this C01 local fix, because no PR update or rerun was approved.
- Final physical Qdrant point-ID policy: logical pre-upsert IDs are deterministic `document_id:chunk_index`, but `embeddings.py` may store deterministic UUIDv5 physical IDs in local mode.
- Full legacy-worker ownership decision for `financial-engine_v2/worker/app/tasks.py` random vector UUID usage.

## Project Memory Save Recommendation

Save this result to Project Memory after review: C01 was a docs/test contract reconciliation, not a backend SQLite purge; future agents must preserve documented SQLite memory/operational-store exceptions while keeping vector/canonical/reproducibility IDs deterministic.
