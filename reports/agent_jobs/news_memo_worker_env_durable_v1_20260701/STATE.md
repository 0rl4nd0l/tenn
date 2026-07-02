# News Memo Worker Env Durable Fix State

started_at: 2026-07-01T20:11:06+10:00
worktree: /home/l4nd0/tenn-news-memo-worker-env-durable-v1-20260701
branch: runtime/news-memo-worker-env-durable-v1-20260701
base_head: 1e5da485183bcce619f4c5c63e2f99aac7e5067f
commit: see `git log -1 --oneline`
lane: STANDARD_FIX / Memory primary

## Current Evidence

- Guard passed in the isolated task worktree with `VALID_TASK_WORKTREE`,
  `stop_reimplementation=false`, and no active duplicate work.
- Post-fix bounded live proof passed on 2026-07-01:
  - `llm_gpu` active queue baseline was 0 and post-run was 0.
  - Parked stale queue stayed parked at depth 42.
  - Durable memo file moved from 411 to 412 valid JSON rows.
  - Source `news:art_78563f510fe7a2e3c622a9ef` was missing before dispatch
    and present after dispatch.
  - Completed task id: `8f59329d-55d4-40d3-b736-0132f340fe46`.
- `/home/l4nd0/tenn` advanced during the prior run, so mutation moved to this
  isolated branch/worktree.
- Similar old branches were inspected:
  - `codex/news-memo-env-gated-fallback-provenance-v1`
  - `codex/news-memo-env-gated-fallback-provenance-integration-v1`
  - `codex/news-memo-signal-routing-candidate-fixture-v1`

## Scope Decision

Patch the durable nightly/worker memo environment contract only. Do not restore
or process the parked stale Redis queue.

## Docs Impact

docs_impact: DOCS_UPDATED
docs_checked:
- docs/README.md
- docs/setup/environment.md
- docs/architecture/09_worker_and_celery_contract.md
docs_changed:
- docs/setup/environment.md
- docs/architecture/09_worker_and_celery_contract.md
docs_followup: none
reason: the nightly/worker memo path and LLM payload contract changed.

## Unsafe Actions Avoided

- Did not restore, delete, or process the parked stale Redis queue.
- Did not start Docker services or mutate Docker volumes.
- Did not run a broad news backfill.
- Did not edit source PDFs, Qdrant, DB rows, gold labels, extraction prompts,
  model files, service units, secrets, or GitHub.

## Closeout

status: committed
commit: see `git log -1 --oneline`
runtime_proof_result: WORKING for the bounded post-fix single-candidate backfill smoke
next_required_proof: next scheduled nightly proof before claiming full
automation is WORKING.
