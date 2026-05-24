# Source Label Semantic Sufficiency Live Failure Fix

Job: `source_label_semantic_sufficiency_live_failure_fix_v1_20260524`
Date: 2026-05-24
Status: PASS

## Session Declaration

Lane: Provenance
Branch: `migration/clean-runtime-baseline-reconstruct-v1`
Worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
Execution mode: SAFE EXTENSION / REGRESSION FIX
Intended files: task card, report artifacts, `chat_evidence_guard.py`, `cockpit_api.py`, focused backend tests
Contested surfaces touched: `financial-engine_v2/backend/app/routes/cockpit_api.py` taxonomy text only
Collision risk: MEDIUM
Decision: proceed

## Confirmed Facts

- `/home/l4nd0/tenn` resolves to `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Branch was `migration/clean-runtime-baseline-reconstruct-v1`.
- Preflight HEAD was `ba5095ea105df5ac3fa83f6b464330c8f2b5bed2`.
- Canonical commit `a6db9760621e274c4621e98eee338a7b7ba34010` is an ancestor of HEAD.
- Registry `check-overlap` passed. One active Reporting job existed for QuantDinger report artifacts only and did not overlap source-label/chat/evidence/test files.
- Task-card validation passed and registry claim succeeded.
- `graphify-out/GRAPH_REPORT.md` and `.cursor/rules/*` were absent in this worktree; `SYSTEM_CONTRACT.md`, `CLAUDE.md`, entrypoint docs, security docs, Claude memory index, and failed smoke artifacts were read.
- The final backend-only reload restarted only `fe_backend`, not Qdrant, Postgres, workers, frontend, llama, Ollama, cron, GPU, or model services.
- Live import proof inside `fe_backend` showed recent-update requirements now resolve to `('recent_news_event',)`.

## Inferred Facts

- The failed smoke was not a classifier miss: both failed answers contained text detected as `recent_news_or_update`.
- The primary bug was mixed-source label ambiguity: `local_news_context`, broad `news`, and filing/announcement wording could satisfy recent-news/update requirements even when every source was `context_only` or unverified.
- A secondary bug was final presentation: existing `DATA_MISSING` text short-circuited additional gap rendering, so financial-truth numeric context could remain visibly worded as announcement/news/event support.

## DATA_MISSING

- `graphify-out/GRAPH_REPORT.md` is absent in this worktree.
- `.cursor/rules/00_mandatory_index.md`, `backend_architecture.md`, `embedding_rules.md`, `vector_store_invariants.md`, and `failure_policy.md` are absent in this worktree.
- No dedicated Postgres/Qdrant write counter was found; mutation proof uses safe `stat` plus `du -sb` directory comparisons.
- Commit hash is recorded in final closeout after commit creation; a self-referential final commit hash cannot be embedded in the same commit that creates this report.

## Root Cause Classification

- Mixed-source label ambiguity: `local_news_context` and broad `news` categories were treated as enough for recent-news/update claims.
- Metadata propagation gap: recent-update requirements used generic `news`/`event_source` categories instead of a stricter recent event evidence category.
- Final answer presentation gap: the visible guard returned early when a response already started with `DATA_MISSING`, leaving missing recent-news/event wording and financial-truth/event wording uncorrected.
- Not a retrieval-ranking rewrite issue. The retrieved sources stayed visible; the fix only changes sufficiency semantics and presentation.
- Not a frontend rendering issue. No frontend files were touched.

## Fix

- Added deterministic `recent_news_event` evidence category.
- Recent-news/update claims now require `recent_news_event`, not broad `news` or `event_source`.
- `recent_news_event` is only emitted for claim-verified news/event sources and is blocked by any explicit `context_only` label.
- Raw `supports_claim` or `claim_verified` payload booleans still cannot self-promote without the deterministic `claim_verified` evidence label.
- Existing visible `DATA_MISSING` blocks are now augmented with missing labels instead of bypassing new gap text.
- Financial-truth/event wording is qualified when recent-news evidence is missing:
  - financial truth is numeric context only;
  - announcement/news context is context only unless separately claim-verified and recent;
  - local news snippets are not sufficient recent-event verification.
- Backend taxonomy text for `local_news_context` now states it is not claim verification unless paired with `claim_verified`.

## Files Changed

- `docs/agent_tasks/source_label_semantic_sufficiency_live_failure_fix_v1_20260524.md`
- `financial-engine_v2/backend/app/services/chat_evidence_guard.py`
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/backend/tests/test_chat_evidence_guard.py`
- `reports/agent_jobs/source_label_semantic_sufficiency_live_failure_fix_v1_20260524/README.md`
- `reports/agent_jobs/source_label_semantic_sufficiency_live_failure_fix_v1_20260524/status.json`
- `reports/agent_jobs/source_label_semantic_sufficiency_live_failure_fix_v1_20260524/validation.json`
- `reports/agent_jobs/source_label_semantic_sufficiency_live_failure_fix_v1_20260524/live_smoke_A_response.json`
- `reports/agent_jobs/source_label_semantic_sufficiency_live_failure_fix_v1_20260524/live_smoke_B_response.json`

## Tests Added

- Recent-news/update with `local_news_context` plus filing-only context remains `insufficient_for_recent_news`.
- Raw `supports_claim` / `claim_verified` booleans do not self-promote into `recent_news_event`.
- Claim-verified news/event source remains sufficient for a valid recent-update path.
- Mixed `claim_verified` plus `context_only` label does not satisfy recent-event sufficiency.
- Existing `DATA_MISSING` blocks are augmented and financial-truth/event wording is qualified.

## Validation Results

- Task-card validation: PASS.
- Registry `check-overlap`: PASS.
- Registry claim: PASS.
- Focused backend pytest:
  - `financial-engine_v2/backend/tests/test_chat_evidence_guard.py`
  - `financial-engine_v2/backend/tests/test_build_ui_sources.py`
  - Result: `70 passed`.
- Focused Ruff:
  - `financial-engine_v2/backend/app/services/chat_evidence_guard.py`
  - `financial-engine_v2/backend/app/routes/cockpit_api.py`
  - `financial-engine_v2/backend/tests/test_chat_evidence_guard.py`
  - `financial-engine_v2/backend/tests/test_build_ui_sources.py`
  - Result: PASS.
- Frontend tests: not run because no frontend files were touched.
- `git diff --check`: PASS.

## Live Smoke Rerun Results

Final backend reload:
- Command: `docker restart fe_backend`
- Post-restart health: `{"status":"ok"}`
- Post-restart start time: `2026-05-24T12:56:19.592826884Z`
- Live import proof: `CLAIM_REQUIREMENTS[RECENT_NEWS_OR_UPDATE] == ('recent_news_event',)`

Smoke A:
- Prompt: `What is the latest news/update on CSL and why did it move recently?`
- Header: `X-Tenn-Stateless-Smoke: 1`
- HTTP: `200`
- Stateless session id: `stateless-smoke-94e616dec7b5405fba87761b0ce06493`
- `chat_persistence`: `disabled`
- `source_coverage_status`: `missing_required_evidence`
- `claim_verified_source_count`: `0`
- `missing_evidence_categories`: `recent_news`
- `unsupported_claim_families`: `recent_news_or_update`
- `evidence_requirement_labels`: `insufficient_for_recent_news`, `missing_required_evidence`, `unsupported_or_not_verified`
- Visible answer starts with `DATA_MISSING / evidence gaps` and explicitly says price, filing, local-news-context, context-only, and numeric financial-truth context are not enough.
- Local/news snippets are rendered as `Local news/context snippets (not sufficient recent-event verification)`.

Smoke B:
- Prompt: `What recent event explains the latest change in BHP, and what financial truth source verifies it?`
- Header: `X-Tenn-Stateless-Smoke: 1`
- HTTP: `200`
- Stateless session id: `stateless-smoke-44fa1b2c118b40649ec8c610dae1ac10`
- `chat_persistence`: `disabled`
- `source_coverage_status`: `missing_required_evidence`
- `claim_verified_source_count`: `0`
- `missing_evidence_categories`: `metric_extraction`, `recent_news`
- `unsupported_claim_families`: `financial_metric`, `recent_news_or_update`
- `evidence_requirement_labels`: `insufficient_for_recent_news`, `metric_extraction_missing`, `missing_required_evidence`, `unsupported_or_not_verified`
- Visible answer states `financial truth numeric context (numbers only; not event/news/announcement verification)`.
- Visible answer states announcement/news context is context-only unless separately claim-verified and recent.
- The old phrase `Available announcement/news context from financial truth:` is replaced by `Available filing/announcement context from financial truth (not event/news verification):`.

## Mutation Proof

- `state.db` hash unchanged: `7ccf7d7eded32fb0a62963dca25c741efa1537970bbb128605b953402b1c915a`.
- `state.db-wal` hash unchanged: empty-file hash.
- `state.db-shm` hash unchanged: `fd4c9fda9cd3f9ae7c962b0ddf37232294d55580e1aa165aa06129b8549389eb`; only mtime changed.
- State table counts unchanged:
  - `chat_messages`: `1535`
  - `chat_sessions`: `75`
  - `analysis_exports`: `262`
  - `update_events`: `4`
- Final stateless session rows were zero in `chat_messages`, `chat_sessions`, `analysis_exports`, and `update_events`.
- Both checked `memory_read_events.jsonl` files were unchanged.
- Company, market, and user thesis memory SQLite hashes were unchanged.
- `news_memos.jsonl` and `news_memo_skips.jsonl` hashes were unchanged.
- Postgres directory stat/size unchanged: `/var/lib/postgresql/data|4096|1779604896|10912569`, `71518966`.
- Qdrant directory stat/size unchanged: `/qdrant/storage|4096|1777968223|10912571`, `762603324`.

## Final Verdict

PASS.

The live-path semantic sufficiency regression is fixed with focused deterministic guard logic and live stateless proof. No forbidden mutation was detected.

## Remaining Risks

- The sufficiency model still depends on upstream code assigning `claim_verified` for genuinely sufficient recent event/news evidence.
- The live response text is safer, but long LLM-generated context can still be verbose; this fix does not redesign answer synthesis.

## Recommended Next Task

Add a small upstream source-role fixture for a genuinely claim-verified recent event/news source so future regressions can validate the positive live-style event path through source construction, not only through the helper.
