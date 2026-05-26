# Natural-Language Local-News Intent Route

## Status

Classification: `FIX LANDED`.

Natural-language ticker local-news prompts now route through the same existing
ticker-news source-pack path as direct `news for TICKER` and strict
`Use only local_news_context for TICKER` prompts.

## Branch / HEAD / Worktree

- Canonical branch: `migration/clean-runtime-baseline-reconstruct-v1`
- Canonical worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- Implementation branch: `safe/natural-language-local-news-intent-route-v1-20260526`
- Implementation worktree: `/home/l4nd0/tenn-natural-language-local-news-intent-route-v1-20260526`
- Base HEAD: `1a758c6eeca9a541a08138c8136e2b6721cd54f0`
- Integrated HEAD: `389117ca25218e47219045976e53327591f916e9`
- Task card: `docs/agent_tasks/natural_language_local_news_intent_route_v1_20260526.md`

## Registry Status

- Canonical registry initially had no active jobs but check-overlap was blocked
  by the two known unrelated untracked task cards.
- Work moved to an isolated clean worktree.
- Isolated registry check-overlap and claim passed.

## Changed Files

- `financial-engine_v2/cockpit/core/chat.py`
- `financial-engine_v2/cockpit/tests/test_chat_ticker_detection.py`
- `financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py`
- `docs/agent_tasks/natural_language_local_news_intent_route_v1_20260526.md`
- `reports/agent_jobs/natural_language_local_news_intent_route_v1_20260526/*`

## Files Intentionally Not Touched

- `financial-engine_v2/backend/app/services/chat_evidence_guard.py`
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- DB, Qdrant, news-store, projection, parser, financial truth, memory, model,
  GPU, env/config, compose, volume, and UI surfaces
- Unrelated untracked task cards:
  - `docs/agent_tasks/a2m_backend_reload_news_status_activation_smoke_v1_20260525.md`
  - `docs/agent_tasks/automation_audit_issue_preservation_v1_20260525.md`

## Confirmed Facts

- Pre-fix matrix: all six natural-language positive prompts detected tickers
  but did not use the direct ticker-news short-circuit.
- Direct `news for A2M`, `news for BHP`, and strict
  `Use only local_news_context for BHP` baselines already used the short-circuit.
- Root cause was limited to Cockpit chat intent routing, not backend source-pack
  verification.
- Post-fix matrix: all six natural-language positive prompts use the ticker-news
  short-circuit.
- Live smoke after backend-only restart: A2M, BHP, CSL natural prompts pass with
  `claim_verified + local_news_context`; COH remains guarded `DATA_MISSING`.

## Inferred Facts

- The running backend was stale before restart because the pre-restart BHP
  natural prompt still returned context-only/missing-required evidence despite
  canonical HEAD containing the fix.

## DATA_MISSING

- `.cursor/rules/` was not present in this checkout, so the architecture-check
  rule-file review is `DATA_MISSING`; `SYSTEM_CONTRACT.md` was read and applied.
- `graphify-out/GRAPH_REPORT.md` and `graphify-out/wiki/index.md` were absent.

## Pre-Fix Matrix

See `pre_fix_intent_matrix.json`.

- FAIL before fix: `latest local news for A2M`, `latest local news for BHP`,
  `what is the latest news on CSL`, `recent local news for BHP`,
  `show me local news for A2M`, `any recent company news for CSL`.
- PASS before fix: `news for A2M`, `news for BHP`,
  `Use only local_news_context for BHP`.
- Controls were not over-routed.

## Root Cause

`_try_news_shortcircuit()` only accepted direct ticker-news wording or literal
`local_news_context` wording. Natural-language local/company/recent/latest news
phrases did not enter the existing `get_news_context()` path.

## Fix

Added a generic natural ticker-news predicate in `cockpit/core/chat.py` that:

- requires an explicit ticker resolved by existing ticker detection;
- requires news intent wording;
- excludes filing/document, financial-analysis, price/chart, and market-wide
  news wording;
- reuses the existing `_try_news_shortcircuit()` source-pack path.

No backend guard or source-label verification code was changed.

## Tests Run

- Task-card validate: PASS.
- Registry list/check-overlap/claim: PASS in isolated worktree.
- JSON validation for report artifacts: PASS.
- `py_compile`: PASS.
- Ruff on changed files: PASS.
- `test_chat_ticker_detection.py`: `38 passed, 48 subtests passed`.
- `test_cockpit_api_chat_stream.py`: `64 passed`.
- `test_build_ui_sources.py`: `58 passed`.
- `test_chat_evidence_guard.py`: `23 passed`.
- `test_cockpit_news_status.py`: `2 passed, 5 warnings`.
- `test_sources.py`: `3 passed`.
- `git diff --check`: PASS.
- Task-card check-diff: PASS in the isolated implementation worktree. The final
  canonical checkout check-diff still reports the two known unrelated untracked
  task cards as outside allowed files; those files were preserved untouched.

## Live Smoke

- Backend-only restart: yes.
- Command: `docker compose -f financial-engine_v2/docker-compose.yml restart backend`
- Backend start after restart: `2026-05-26T05:52:56.685103721Z`
- Services not restarted: Qdrant, Postgres, worker, GPU worker, Next,
  llama-server.

Smoke summary:

- PASS: `latest local news for A2M`
- PASS: `latest local news for BHP`
- PASS: `what is the latest news on CSL`
- PASS: `news for BHP`
- PASS: `Use only local_news_context for BHP`
- PASS: SSE `latest local news for BHP`
- DATA_MISSING: `latest local news for COH`

See `smoke_results.json`.

## Forbidden Mutation Attestation

No DB, Qdrant, news-store, reindex, resync, backfill, projection repair,
migration, parser routing, canonical financial truth, Tenn memory,
runtime/model/GPU config, env/config, volume, compose, or UI mutation occurred.

`chat_evidence_guard.py` remained intact.

## What This Proves

- Natural-language local-news ticker prompts now share the claim-verified
  local-news source-pack path with direct and strict prompts.
- A2M, BHP, and CSL passed against live backend code.
- COH/no-hit remains honest `DATA_MISSING`.
- Non-news and filing/document controls are not forced into news retrieval.

## What This Does Not Prove

- It does not repair canonical SQLite news projection absence.
- It does not validate every ASX ticker.
- It does not change UI source-drawer rendering.

## Final Git Status

Expected remaining canonical dirt:

- `?? docs/agent_tasks/a2m_backend_reload_news_status_activation_smoke_v1_20260525.md`
- `?? docs/agent_tasks/automation_audit_issue_preservation_v1_20260525.md`

## Merge / Parking Status

Merged into canonical by fast-forward from the isolated safe branch.

## Project Memory Save Recommendation

Save that natural-language local/company/recent/latest ticker-news prompts
should use the existing `ChatController._try_news_shortcircuit()` path and must
not alter `chat_evidence_guard.py` or source-label honesty semantics.
