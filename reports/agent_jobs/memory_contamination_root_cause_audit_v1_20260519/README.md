# Memory Contamination Root Cause Audit v1

## Executive Verdict

- `ROOT_CAUSE_CONFIRMED`: historical memo-level ticker fanout is proven by current code history artifacts, current writer-path shape, and retained report manifests. The old bug wrote each accepted statement once per memo-level ticker into `company_memory`.
- `SURFACING_CONFIRMED`: if a contaminated row is active under a ticker scope, current reader paths can surface it in ticker-specific chat/company-analysis contexts. Current live contaminated-active-row status is `DATA_MISSING` because this audit did not open production DBs.
- `CLEANUP_BLOCKED`: no cleanup is approved or safe here. Current live row inventory, backup/checksum, operator review, and a mutation-specific task card are still required.

## Confirmed Facts

Preflight and task control:

- Worktree: `/home/l4nd0/tenn-memory-contamination-root-cause-audit-v1-20260519`.
- Runtime symlink target: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Branch: `audit/memory-contamination-root-cause-audit-v1-20260519`.
- HEAD: `2e73de32ac77`.
- Runtime checkout had unrelated untracked task cards; this isolated worktree was created from the same HEAD.
- Task card validation passed with `mutation_mode=audit_only`, `production_data_access=false`, and only task-card/report paths allowed.
- Registry list-active was empty, overlap check passed, and this job was claimed.

Files and artifacts inspected:

- `docs/architecture/22_memory_ownership_map.md`
- `docs/architecture/18_cockpit_memory.md`
- `financial-engine_v2/backend/app/services/company_memory.py`
- `financial-engine_v2/backend/app/services/market_memory.py`
- `financial-engine_v2/backend/app/services/user_thesis_memory.py`
- `financial-engine_v2/backend/app/services/source_registry.py`
- `financial-engine_v2/backend/app/services/memory_events.py`
- `financial-engine_v2/backend/app/services/memory_signal_router.py`
- `financial-engine_v2/backend/app/services/commentary_memo_extractor.py`
- `financial-engine_v2/backend/app/services/news_memo_extractor.py`
- `financial-engine_v2/backend/app/services/memory_assembler.py`
- `financial-engine_v2/backend/app/services/query_orchestrator.py`
- `financial-engine_v2/backend/app/api/context.py`
- `financial-engine_v2/cockpit/integrations/backend_api.py`
- `financial-engine_v2/cockpit/core/tool_executor.py`
- `financial-engine_v2/cockpit/core/chat.py`
- `cockpit-ui/app/api/cockpit/memory/route.ts`
- `cockpit-ui/app/api/cockpit/memory/company-dump/route.ts`
- `cockpit-ui/components/cockpit/memory/memory-screen.tsx`
- `financial-engine_v2/backend/tests/test_memory_signal_router.py`
- `financial-engine_v2/backend/tests/test_context_endpoints.py`
- `financial-engine_v2/backend/tests/test_query_orchestrator.py`
- `financial-engine_v2/backend/tests/test_memo_extractors_signal_routing.py`
- `scripts/audit_memory_integrity.py`
- `scripts/test_audit_memory_integrity.py`
- `reports/memory_contamination_root_cause_20260505_161634/*`
- `reports/memory_signal_router_fanout_guard_20260505_164348/*`
- `reports/memory_historical_cleanup_plan_20260505_170452/*`
- `reports/memory_interticker_contamination_manifest_20260513_043646/*`
- `reports/agent_jobs/memory_integrity_audit_guard_v1_20260516/*`
- `reports/agent_jobs/memory_company_context_active_only_read_guard_v1_20260517/validation.json`
- `reports/agent_jobs/memory_nvme_fastdev_context_root_integration_v1_20260517/validation.json`

Memory stores discovered:

- Company memory: `reports/research_memory/company_memory.sqlite`.
- Market memory: `reports/research_memory/market_memory.sqlite`.
- User thesis memory: `reports/research_memory/user_thesis_memory.sqlite`.
- Source registry: `reports/research_memory/source_registry.jsonl`.
- News memos: `reports/research_memory/news_memos.jsonl`.
- Memory events: `reports/research_memory/memory_read_events.jsonl`, `memory_write_events.jsonl`.
- Cockpit-local filesystem memory: `~/.tenn/memory`.
- Qdrant retrieval stores are semantic indexes, not company memory.

Writer paths discovered:

- Automatic commentary path: `CommentaryMemoExtractor.extract_and_store()` -> `signals_from_commentary_memo()` -> `route_signals()` -> `CompanyMemoryStore.update_company_memory()`.
- Automatic news path: `NewsMemoExtractor.extract_and_store()` -> `signals_from_news_memo()` -> `route_signals()` -> `CompanyMemoryStore.update_company_memory()`.
- Manual company path: `/api/context/memory/company/add` -> `add_manual_company_memory_entry()`.
- Manual expiry path: `/api/context/memory/company/expire` -> `expire_company_memory_entry()`.

Reader paths discovered:

- `CompanyMemoryStore.retrieve()` uses `entities["primary_ticker"]`, lists active entries for that exact company ID, ranks them, and returns `items`.
- `MemoryAssembler` filters company-memory items to `status=active` and `active_score >= 0.55`.
- `QueryOrchestrator` includes company memory for strategy, risk/catalyst, financial interpretation, and mixed/company-analysis paths, then writes selected statements into answer input.
- `/api/context/memory` and `/api/context/company_dump` call `_load_company_memory()`, which now defaults to `entry_status="active"`.
- The web Memory tab proxies `/api/context/memory`, `/api/context/memory/index`, and `/api/context/company_dump`.
- Cockpit tool execution and `/filestats` call `BackendApiClient.get_company_dump()`.

Prior contamination evidence found:

- May 5 root-cause report: old router fanout confirmed; largest cluster was `PETTIMED's capital raising at 1 cent per share`, 67 rows across 50 entities from one YouTube transcript.
- May 5 root-cause report: stocktake had 107 duplicate/fanout clusters; 43 commentary/youtube clusters totaling 1555 rows and 64 newspaper4k clusters totaling 322 rows.
- May 5 cleanup plan: copied DB counts included 1998 company-memory rows, 83 company scopes, 108 DB duplicate clusters, and 1212 status-expire candidates.
- May 13 manifest: live inspected DB had 2333 rows, 2083 active rows, 94 active duplicate clusters, 1615 active duplicate rows, 963 approval-required status-expire candidates, and 652 new/unclassified active duplicate rows.
- May 16 integrity audit artifact: active company-memory entries were down to 40 with zero duplicate statement clusters and zero source-fanout clusters, but this was not refreshed in this audit.

## Inferred Facts

- Likely root cause: historically, memo extraction produced a memo-level `tickers` list and the old router treated every ticker as a target for every statement. Company-memory storage preserved those emitted scopes and only deduped within one company ID.
- Likely blast radius: class-wide across automatic commentary/news memo routing before the guard landed. The May 13 manifest shows both `commentary:youtube_transcript` and `news:newspaper4k` rows.
- Likely current guard status: current code has the fanout guard and passing tests. New writes from the inspected router path should not repeat the same memo-level fanout pattern.
- Likely remaining risk: contaminated historical rows can still surface if they remain active under an exact ticker scope. Current active contamination is not refreshed here.

## Speculative Claims

- Some remaining manual-review rows may still be legitimate but noisy company-specific evidence. This cannot be resolved without source/span review.
- Thesis-audit surfacing is lower-confidence than chat/company_dump surfacing because this audit did not run or deeply trace every thesis-audit reader path.

## DATA_MISSING

See `DATA_MISSING.md`.

Key gaps:

- No production SQLite DB was opened.
- No live API/chat smoke was run.
- Raw stocktake folder `reports/full_system_stocktake_20260505_152038` is absent from this checkout.
- Current active contaminated-row count is not proven.
- Full production memo dispatch/candidate-ticker behavior is not proven.

## Memory Store Inventory

See `memory_store_inventory.json`.

Company-memory schema fields that matter for contamination:

- Scope: `company_id`, `entity_id`.
- Statement identity: `statement`, `normalized_statement`, `type`.
- Provenance: `source`, `source_id`, `first_seen_at`, `last_seen_at`, `metadata_json`.
- Lifecycle: `status`, `closed_at`, `change_log`.
- Missing from schema: durable source memo row ID, writer job ID, batch ID, statement-level source span, and explicit ticker-attribution reason.

## Writer Path Trace

See `writer_path_trace.md`.

Current router behavior:

- single-ticker memo: company statements can route to that ticker;
- multi-ticker memo with exactly one explicit statement target: routes to that one ticker;
- multi-ticker memo with no unique statement target: creates no company-memory write;
- sector/macro inference remains separate market-memory routing.

The current guard is covered by tests:

- `test_multi_topic_commentary_does_not_fanout_primary_company_signal`
- `test_multi_ticker_memo_without_statement_target_does_not_fanout`
- `test_multi_ticker_memo_honors_statement_level_target_ticker`

## Reader / Surfacing Path Trace

See `surfacing_risk_matrix.json`.

Important distinction:

- Write-path contamination and read-path safety are separate.
- Current reader paths mostly default to active company-memory rows, so expired historical rows should not be answer context by default.
- Active contaminated rows, if any remain, can still surface because readers trust the row's `company_id` scope.

## Fanout / Blast Radius Assessment

Classification: `confirmed class-wide historically; current active blast radius DATA_MISSING`.

Evidence:

- May 5 artifacts tied the largest clusters to old router fanout.
- May 13 manifest showed 94 active duplicate clusters and 1615 active duplicate rows.
- Artifact parser summary in this task found `commentary:youtube_transcript` at 1349 active duplicate rows and `news:newspaper4k` at 266 rows in the manifest.
- Top affected company IDs in the May 13 duplicate-row manifest included `COH` with 54 rows, `ASX` with 52, and `A2M` with 45.

What would prove current blast radius:

- Approval-gated read-only immutable query against production `company_memory.sqlite`.
- Compare active duplicate clusters, source-fanout clusters, and manual-review active IDs.
- Sample ticker-specific `/api/context/company_dump` for known historical tickers without triggering write paths.

## Prevention Plan

Tests to keep:

- Multi-topic commentary no-fanout fixture.
- Ambiguous multi-ticker memo produces no company-memory writes.
- Statement-level target ticker is honored.
- Single-company memo still routes all supported company statements to that company.
- Memory-integrity audit detects active duplicate statement fanout and source-fanout clusters.
- Context endpoint defaults to active company-memory entries.

Tests to add next:

- News memo fixture with `candidate_tickers=["A2M", "BHP"]` where an A2M statement must not write to BHP.
- Structured statement fixture that preserves statement-level `target_ticker`, `source_id`, `published_at`, and future evidence span metadata.
- Market-only multi-ticker sector/macro fixture that creates market memory but no company-memory rows.
- Query-orchestrator fixture showing memory context is `memory_context/context_only`, never `claim_verified`.
- Non-mutating replay harness for historical memos against temp SQLite stores.

## Cleanup Plan Later

See `cleanup_plan_later.md`.

Summary:

- Backup/export first.
- Read-only row-ID manifest second.
- Operator review third.
- Only then consider capped status-only expiry.
- No delete, rewrite, alias canonicalization, Qdrant reindex, or news resync.

## Hard Stops / Do Not Do

- Do not clean up now.
- Do not expire rows now.
- Do not canonicalize aliases now.
- Do not rewrite company names or statements now.
- Do not touch Qdrant/news stores.
- Do not run backfills or resyncs.
- Do not mutate financial truth, parser/extraction outputs, runtime config, or Cockpit chat guard code.

## Validation Commands Run

- `pwd` -> `/home/l4nd0`
- `readlink -f /home/l4nd0/tenn-runtime` -> `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- `git -C /home/l4nd0/tenn-runtime branch --show-current` -> `migration/clean-runtime-baseline-reconstruct-v1`
- `git -C /home/l4nd0/tenn-runtime rev-parse --short=12 HEAD` -> `2e73de32ac77`
- `git -C /home/l4nd0/tenn-runtime status --short` -> unrelated untracked task cards present
- `git -C /home/l4nd0/tenn-runtime worktree list` -> isolated audit worktree created
- `git -C /home/l4nd0/tenn-runtime show --stat --oneline --no-renames HEAD` -> `2e73de32 milestone(evaluation): checkpoint nvme runtime audit artifacts`
- `git worktree add -b audit/memory-contamination-root-cause-audit-v1-20260519 /home/l4nd0/tenn-memory-contamination-root-cause-audit-v1-20260519 HEAD` -> passed
- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/memory_contamination_root_cause_audit_v1_20260519.md` -> `ok: true`
- `python3 scripts/agent_job_registry.py list-active` -> `active_jobs: []`
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/memory_contamination_root_cause_audit_v1_20260519.md` -> `ok: true`
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/memory_contamination_root_cause_audit_v1_20260519.md` -> `ok: true`
- `PYTHONPATH=financial-engine_v2/backend TENN_RESEARCH_MEMORY_ROOT=/tmp/... /mnt/hdd-data/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python -m pytest -q financial-engine_v2/backend/tests/test_memory_signal_router.py scripts/test_audit_memory_integrity.py financial-engine_v2/backend/tests/test_context_endpoints.py::TestGetMemoryContext` -> `21 passed in 9.61s`
- `find financial-engine_v2/data ... research_memory` after tests -> no research-memory files created in the worktree
- `jq empty reports/agent_jobs/memory_contamination_root_cause_audit_v1_20260519/*.json` -> passed
- `git diff --check` -> passed
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/memory_contamination_root_cause_audit_v1_20260519.md` -> `ok: true`
- `python3 scripts/agent_job_registry.py release memory_contamination_root_cause_audit_v1_20260519` -> `ok: true`
- `python3 scripts/agent_job_registry.py list-active` after release -> `active_jobs: []`

## Final Git Status

Final status:

- `?? docs/agent_tasks/memory_contamination_root_cause_audit_v1_20260519.md`
- `!! reports/agent_jobs/memory_contamination_root_cause_audit_v1_20260519/`

The report directory is ignored by repo rules but exists on disk and is within the task card's allowed files. `check-diff` passed with no disallowed files.

## Registry Release Status

Claimed and released. `status.json` records `status: released`, and the registry has no active jobs after release.

## Project Memory Save Recommendation

`SAVE_REQUIRED`: the audit clarifies that historical root cause is confirmed, current router guard is present, read-path surfacing is confirmed for active contaminated rows, and current live DB contamination is DATA_MISSING under this audit-only card.
