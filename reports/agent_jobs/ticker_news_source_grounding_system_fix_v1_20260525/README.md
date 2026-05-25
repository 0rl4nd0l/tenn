# Ticker News Source Grounding System Fix

## Branch / HEAD / Worktree

- Branch: `safe/ticker-news-source-grounding-system-fix-v1-20260525`
- Base HEAD: `5a6c0c00b58c056fcf93933a9d1dd5754daa3338`
- Closeout HEAD: branch tip containing this report commit; exact SHA verified
  with `git rev-parse HEAD` after commit.
- Worktree: `/home/l4nd0/tenn-ticker-news-source-grounding-system-fix-v1-20260525`
- Canonical launcher path verified: `/home/l4nd0/tenn` and
  `/home/l4nd0/tenn-runtime` resolve to
  `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- Route-contract commit `c8d605e3de625c9f456edc0f3896b571a68f6b25` is an
  ancestor of the worktree HEAD.

## Task Card

- `docs/agent_tasks/ticker_news_source_grounding_system_fix_v1_20260525.md`
- Repo validator does not accept literal `mutation_mode: implementation`, so the
  card uses `mutation_mode: safe_extension` with
  `requested_mutation_mode: implementation`.

## Registry Status

- Registry claim succeeded for
  `ticker_news_source_grounding_system_fix_v1_20260525`.
- Active overlap check passed.
- One unrelated active Reporting job was present on `cockpit-ui/**`; no lane or
  file overlap with this Query Orchestration task.
- Final release state is recorded in `status.json` when the closeout command is
  run.

## Changed Files

- `financial-engine_v2/backend/app/services/chat_evidence_guard.py`
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/backend/tests/test_chat_evidence_guard.py`
- `financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py`
- `financial-engine_v2/backend/tests/test_sources.py`
- `docs/agent_tasks/ticker_news_source_grounding_system_fix_v1_20260525.md`
- `reports/agent_jobs/ticker_news_source_grounding_system_fix_v1_20260525/*`

## Files Intentionally Not Touched

- `cockpit-ui/**`
- DB, Qdrant, news-store, projection, parser, memory, runtime, model, GPU, and
  env/config surfaces.
- Existing unrelated task cards in the canonical worktree.

## Confirmed Facts

- Qdrant `news_chunks` has local/news evidence for A2M, BHP, CSL, XRO, and NST.
- COH is a no-local-news control in the refreshed probe (`qdrant_count: 0`).
- Canonical SQLite news projection files are absent in the current status route.
- Live current-runtime chat misattributes document/filing context as local news
  for A2M, BHP, CSL, NST, and COH.
- Source labels and `claim_verified_source_count` often remain honest, but final
  synthesis ignored those labels.
- Existing visible gap labels could warn but did not prevent the dishonest answer
  body from continuing.

## Inferred Facts

- Ranking broad multi-ticker news above direct primary ticker items is a
  secondary retrieval/ranking weakness, not the primary fix point for this task.
- The systemic safe fix is a deterministic local-news-only final-answer guard at
  Cockpit response assembly, not an A2M alias patch or store repair.

## DATA_MISSING

- Live external chat proof of the changed branch is missing because the running
  backend process could not be proven to be serving this isolated worktree, and
  no restart was performed.
- No DB migration, news projection repair, or Qdrant reindex was authorized or
  run.

## Ticker Basket

- A2M: seed canary with direct A2M local/news rows.
- BHP, CSL, XRO, NST: representative ASX tickers with local/news context in
  Qdrant.
- COH: low/no-local-news control.

## Blast-Radius Result

- 6 tickers probed.
- 5 had Qdrant local/news evidence.
- 5 showed systemic synthesis honesty failures or no-hit misattribution.
- XRO already returned an honest DATA_MISSING-style answer in the live probe.
- See `blast_radius_matrix.json`.

## Root Cause

The shared root cause is final synthesis honesty, with prompt/context assembly
allowing mixed source packs to satisfy local-news-only requests. Retrieval often
returned context-only local news and documents/filings together; the final answer
then used documents, filings, financial statements, or price context as if they
were local news.

## Fix Implemented

- Added `apply_local_news_only_guard()` in
  `financial-engine_v2/backend/app/services/chat_evidence_guard.py`.
- Added `requires_local_news_only_guard()` for route-level stream handling.
- Applied the guard in non-stream and SSE final Cockpit chat responses.
- Suppressed incremental SSE chunks for local-news-only requests so unguarded
  model text cannot leak before the guarded final `done` event.
- Preserved visible sources and source labels.
- When no claim-verified local news exists, the final answer is rewritten to
  `DATA_MISSING`, `claim_verified_source_count` remains zero, and
  `source_coverage_status` remains honest as `missing_required_evidence` unless
  an existing degraded/runtime status must be preserved.

## Tests Run

- `python3 -m py_compile ...` for changed backend Python files: pass.
- Ruff on changed backend Python files: pass.
- Guard and Cockpit route tests: `85 passed, 1 warning`.
- Expanded status/source/route suite:
  `test_chat_evidence_guard.py`, `test_cockpit_api_chat_stream.py`,
  `test_cockpit_news_status.py`, `test_build_ui_sources.py`,
  `test_sources.py`, `test_route_parity_contract.py`: `147 passed, 6 warnings`.
- `git diff --check`: pass.
- Task-card validate and check-diff: pass.

## Live Smoke

- `GET /api/cockpit/news/status`: pass.
- `GET /api/cockpit/config`: pass.
- `GET /openapi.json`: pass.
- Stateless live chat probes were run against current runtime and reproduced the
  regression, but they are not treated as changed-code proof because the backend
  was not restarted onto this branch.

## Forbidden Mutation Attestation

- No DB mutation.
- No Qdrant mutation.
- No news-store mutation.
- No reindex, resync, backfill, projection rebuild, or projection repair.
- No parser routing change.
- No canonical financial truth write.
- No Tenn memory write.
- No runtime/model/GPU config edit.
- No UI redesign.
- No A2M-only alias hardcoding.

## Known Risks

- The guard is intentionally conservative for local-news-only prompts. In SSE
  mode it suppresses incremental text chunks and sends the guarded final answer
  in the `done` event.
- Retrieval/ranking still favors broad multi-ticker articles for several
  tickers. This is recorded as a secondary weakness, not fixed here.
- Changed-code live external chat smoke requires a backend restart or an
  alternate isolated backend process, neither of which was performed.

## What This Proves

- The root cause is systemic final-answer/source-pack honesty, not an A2M-only
  alias gap.
- The changed backend route and evidence guard prevent local-news-only answers
  from using documents/filings as news when local news is context-only or absent.
- Context-only/no-hit/degraded evidence remains labelled honestly.
- Multi-ticker regression coverage passes.

## What This Does Not Prove

- It does not prove the active production-like backend is serving this branch.
- It does not repair canonical SQLite news projection absence.
- It does not improve Qdrant ranking of direct primary ticker news above broad
  multi-ticker articles.
- It does not mutate or rebuild any store.

## Final Git Status

After closeout commit, the branch contains only task-card, report, backend
guard, Cockpit route, and backend test changes inside the task-card allowed
files. The final worktree status was verified clean after the commit.

## Merge / Parking Status

Parking is selected instead of direct canonical integration because the
canonical launcher worktree contains unrelated foreign untracked task cards and
because changed-code live external chat smoke would require an unperformed
backend restart. Next merge-review command:

`git -C /home/l4nd0/tenn-ticker-news-source-grounding-system-fix-v1-20260525 show --stat --oneline HEAD`

## Project Memory Save Recommendation

Save a memory note that Cockpit local-news-only source grounding is now guarded
in `chat_evidence_guard.apply_local_news_only_guard()`, and that broad
multi-ticker news ranking remains a separate retrieval/ranking follow-up.
