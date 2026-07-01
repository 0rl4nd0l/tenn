# Runtime Functionality Proof

result: WORKING

This proof covers the approved bounded post-fix smoke only: one current missing
news article dispatched through `scripts/backfill_missing_news_memos.py`, handled
by one temporary `llm_gpu` worker, and written to the durable NVMe research
memory store. It does not claim the next scheduled nightly automation run has
executed.

| Field | Required evidence |
| --- | --- |
| intended output | One current news memo row written through the updated backfill path to the durable NVMe research memory store. |
| live output location | `/mnt/tenn-nvme2/tenn/financial-engine_v2/data/reports/research_memory/news_memos.jsonl` |
| pre-run max timestamp or count | `memo_before.json`: 411 valid JSON lines, latest `published_at=2026-07-01T06:56:41Z`, sha256 `3bea3a55979ec5fbfff4dcf69be467041a631c8e80ac834cfd0746beca5cc519`; `llm_gpu` depth 0; parked stale queue depth 42. |
| post-run max timestamp or count | `memo_after.json`: 412 valid JSON lines, latest `published_at=2026-07-01T06:56:41Z`, sha256 `575ab19d726ac12e76f1b1654e5c4910151f70d7cf4ffa8f0282ad2c2fdf9499`; `llm_gpu` depth 0; parked stale queue depth still 42. |
| rows/files inserted or updated after run start | 1 memo row inserted/updated for `news:art_78563f510fe7a2e3c622a9ef`; selected article was missing before dispatch (`persisted_before_dispatch=0`) and present after (`persisted_after_dispatch=1`). |
| readiness/gate status | Bounded post-fix single-candidate backfill smoke passed. Full scheduled nightly automation still needs a scheduled-run proof before being called working. |
| exact command/query used | `scripts/backfill_missing_news_memos.py --db-path /mnt/tenn-nvme2/tenn/financial-engine_v2/reports/qual_context/news_articles.sqlite --since-hours 0 --limit 1 --memo-diagnostics-path /mnt/tenn-nvme2/tenn/financial-engine_v2/data/reports/research_memory/news_memos.jsonl --wait-for-memos --memo-wait-timeout-seconds 240 --memo-wait-poll-interval-seconds 2 --dispatch-batch-size 1 --memo-llm-url http://127.0.0.1:8001 --memo-llm-model model:qwen2.5-14b-instruct --summary-json reports/agent_jobs/news_memo_worker_env_durable_v1_20260701/postfix_live_backfill_summary.json` |
| result: WORKING / PARTIAL / BROKEN / DATA_MISSING | WORKING |
| remaining blocker | none for the bounded backfill smoke. |

## Proof Artifacts

- `queue_before.json` / `queue_after.json`: active `llm_gpu` stayed empty after
  completion; parked stale queue was not restored or processed.
- `memo_before.json` / `memo_after.json`: durable memo file count and hash
  changed by exactly one row.
- `candidate_preview.json`: selected source
  `news:art_78563f510fe7a2e3c622a9ef`, published
  `2026-07-01T06:46:35Z`.
- `postfix_live_backfill_summary.json`: `status=complete`, `dispatched=1`,
  `tasks_observed=1`, `tasks_completed=1`, `tasks_failed=0`,
  `tasks_pending=0`, `tasks_unobserved=0`.
- `runtime_proof_live.json`: proof row provenance
  `llm_url=http://127.0.0.1:8001`,
  `llm_model=model:qwen2.5-14b-instruct`.
- `worker.log`: temporary single-worker run received and completed task
  `8f59329d-55d4-40d3-b736-0132f340fe46`, then warm-shut down.
