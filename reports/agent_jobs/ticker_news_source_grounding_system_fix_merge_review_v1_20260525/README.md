# Ticker News Source Grounding System Fix Merge Review

## Branch / HEAD / Worktree

- Canonical branch: `migration/clean-runtime-baseline-reconstruct-v1`
- Canonical preflight HEAD: `dfa76437bebd9e0ec22f6c80ec9ab5e9177a5f4b`
- Canonical drift HEAD before final integration: `4d2d4b69e70535e81aec502cb2e99349d4a11a4c`
- Integrated code HEAD: `bb78656ba28908df3efa54efcbad10fa17f841d1`
- Canonical worktree: `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`
- Isolated merge-review worktree:
  `/home/l4nd0/tenn-ticker-news-source-grounding-system-fix-merge-review-v1-20260525`

## Source

- Parked branch: `safe/ticker-news-source-grounding-system-fix-v1-20260525`
- Parked commit: `703d8ada2fccb29f1a77c8a401e1c4fafd046497`
- Parked worktree:
  `/home/l4nd0/tenn-ticker-news-source-grounding-system-fix-v1-20260525`
- Parked report:
  `reports/agent_jobs/ticker_news_source_grounding_system_fix_v1_20260525/README.md`

## Task Card

- `docs/agent_tasks/ticker_news_source_grounding_system_fix_merge_review_v1_20260525.md`

## Registry Status

- Canonical checkout registry check was blocked by unrelated untracked task
  cards, so this merge review used a clean isolated worktree.
- Isolated worktree task-card validation passed.
- Isolated worktree registry claim succeeded.
- Active Query Orchestration overlap: none.
- One unrelated active Reporting job appeared on `cockpit-ui/**`; no lane/file
  overlap with this task.

## Merge Method

1. `git cherry-pick -x 703d8ada2fccb29f1a77c8a401e1c4fafd046497`
2. Canonical moved to `4d2d4b69`, so the isolated branch was rebased onto
   `migration/clean-runtime-baseline-reconstruct-v1`.
3. Canonical was fast-forwarded with:
   `git -C /home/l4nd0/tenn merge --ff-only safe/ticker-news-source-grounding-system-fix-merge-review-v1-20260525`

## Changed Files

- `financial-engine_v2/backend/app/services/chat_evidence_guard.py`
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/backend/tests/test_chat_evidence_guard.py`
- `financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py`
- `financial-engine_v2/backend/tests/test_sources.py`
- `docs/agent_tasks/ticker_news_source_grounding_system_fix_v1_20260525.md`
- `reports/agent_jobs/ticker_news_source_grounding_system_fix_v1_20260525/*`
- this merge-review task card and report bundle

## Files Intentionally Not Touched

- `docs/agent_tasks/a2m_backend_reload_news_status_activation_smoke_v1_20260525.md`
- `docs/agent_tasks/automation_audit_issue_preservation_v1_20260525.md`
- `cockpit-ui/**`
- DB, Qdrant, news-store, projection, parser, memory, model, GPU, and env/config
  surfaces

## Confirmed Facts

- Parked report classified the shared root cause as prompt/context assembly and
  final synthesis honesty, not A2M aliasing.
- Parked blast radius included A2M, BHP, CSL, XRO, NST, and COH.
- Qdrant local/news evidence existed for A2M, BHP, CSL, XRO, and NST; COH was a
  low/no-local-news control.
- Canonical target moved during review only through a Reporting-lane Cockpit UI
  report commit.
- The integrated fix adds a deterministic local-news-only response guard and
  SSE chunk suppression for guarded requests.

## Inferred Facts

- Retrieval/ranking quality remains a separate follow-up because the integrated
  commit intentionally fixes source-honesty at response assembly, not Qdrant
  ranking.
- The backend process needed a restart because it had started before the merge
  and was plain `uvicorn` without a visible reload flag.

## DATA_MISSING

- No claim-verified local-news source was found in the live A2M, BHP, or COH
  local-news-only smokes.
- Returning `DATA_MISSING` was therefore the correct source-honest behavior.

## Ticker Basket And Rationale

- A2M: seed canary with prior filing/news misattribution.
- BHP: non-A2M large ASX ticker with local_news_context but no claim-verified
  local-news proof in the live smoke.
- COH: no-local-news/control ticker.
- A2M SSE: streaming leak guard check.

## Blast Radius Result

Parked blast radius found 5 systemic synthesis-honesty failures across 6
tickers. The integration validated the guard with focused tests and live
post-restart smoke on A2M, BHP, and COH.

## Root Cause

The shared root cause was final synthesis/source-pack honesty: local-news-only
requests could be answered from document, filing, price, memory, or operational
context even when visible local news was context-only or absent.

## Fix Implemented

- `apply_local_news_only_guard()` rewrites insufficient local-news-only answers
  to `DATA_MISSING`.
- `requires_local_news_only_guard()` detects local-news-only requests.
- Cockpit non-stream responses apply the guard before visible gap labels.
- Cockpit SSE responses suppress incremental chunks for guarded requests and
  send the guarded final answer in the `done` event.
- Source labels, context-only state, degraded state, and claim counts remain
  visible.

## Tests Run

- Task-card validate: pass.
- Registry check/claim in isolated worktree: pass.
- Parked JSON artifact validation: pass.
- `python3 -m py_compile` for changed backend Python files: pass.
- Ruff for changed backend Python files: pass.
- Focused backend suite:
  `test_chat_evidence_guard.py`, `test_cockpit_api_chat_stream.py`,
  `test_cockpit_news_status.py`, `test_build_ui_sources.py`,
  `test_sources.py`, `test_route_parity_contract.py`: `147 passed, 6 warnings`.
- `git diff --check HEAD~1..HEAD`: pass.

## Live Smoke

- Backend-only restart performed: yes.
- Restart command:
  `docker compose --env-file /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/.env.docker -f /home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1/financial-engine_v2/docker-compose.yml restart backend`
- Only `fe_backend` restarted. Qdrant, Postgres, workers, llama, and Next were
  not restarted.
- `GET /api/cockpit/news/status`: pass.
- `GET /api/cockpit/config`: pass.
- `GET /openapi.json`: pass.
- A2M local-news-only stateless chat: pass, guarded `DATA_MISSING`.
- BHP local-news-only stateless chat: pass, guarded `DATA_MISSING`.
- COH no-local-news control: pass, guarded `DATA_MISSING`.
- A2M SSE: pass, zero chunk events before guarded final `done`.

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
- No test relaxation for dishonest source-grounding.

## Known Risks

- The guard is conservative for local-news-only wording and waits for the model
  response before rewriting insufficient answers.
- Retrieval/ranking still needs a separate follow-up for broad multi-ticker news
  results outranking direct ticker articles.
- The config route still reports `git_branch: null`; runtime code presence was
  proven through behavior, route health, and scoped restart, not a git field.

## What This Proves

- The parked commit integrates cleanly on current canonical.
- Multi-ticker regression tests pass after target drift.
- A2M no longer misattributes filing/dividend context as local news in the
  changed runtime.
- Non-A2M BHP and COH checks pass or honestly report missing local-news proof.
- Context-only/no-hit evidence remains labelled as insufficient rather than
  source-backed news.

## What This Does Not Prove

- It does not repair canonical SQLite news projection absence.
- It does not improve Qdrant retrieval/ranking.
- It does not validate every ASX ticker.
- It does not change UI source-drawer rendering.

## Final Git Status

Before committing this merge-review report, the canonical checkout was at
`bb78656ba28908df3efa54efcbad10fa17f841d1` with only these unrelated untracked
task cards remaining:

- `docs/agent_tasks/a2m_backend_reload_news_status_activation_smoke_v1_20260525.md`
- `docs/agent_tasks/automation_audit_issue_preservation_v1_20260525.md`

They were not touched.

## Merge / Parking Status

Classification: `MERGED_AND_VALIDATED`.

The parked fix is no longer parked for code integration. This report bundle is
the merge-review closeout.

## Project Memory Save Recommendation

Save that Cockpit local-news-only source grounding is guarded by
`chat_evidence_guard.apply_local_news_only_guard()` and that broad multi-ticker
news retrieval/ranking remains a separate follow-up.
