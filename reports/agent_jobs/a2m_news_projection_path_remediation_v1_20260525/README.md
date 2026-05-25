# A2M News Projection Path Remediation Audit

Lane: Query Orchestration
Supporting lanes: Provenance, Reporting
Mode: AUDIT ONLY
Production data access: false

## Executive Result

A2M is not missing because of a ticker alias, entity-linking, or query-ranking
failure. Current Qdrant `news_chunks` is reachable and contains A2M evidence,
and current backend chat/news retrieval paths match A2M across `ticker`,
`primary_ticker`, and `tickers`.

The gap is a projection/path gap. The canonical runtime path now resolves
`/home/l4nd0/tenn` and `/home/l4nd0/tenn-runtime` to the NVMe clean baseline,
but that path has no `reports/qual_context/news_articles.sqlite` or
`reports/qual_context/news.sqlite`. A legacy `/mnt/sdb2/home/l4nd0/tenn`
checkout does have both SQLite files, A2M rows, and May 24 nightly artifacts,
but current canonical code/config does not point Cockpit/query consumers at
that legacy path. The current May 25 nightly run wrote only a short NVMe log and
no NVMe summary/SQLite artifacts.

Root cause classification: Confirmed moved/runtime path mismatch plus confirmed
canonical SQLite projection absence; inferred current nightly projection failure
after the NVMe cutover; confirmed Qdrant/legacy SQLite are out of parity for at
least one A2M article.

Smallest safe remediation: add a read-only projection path health smoke that
reports canonical article DB, canonical fallback DB, legacy DB candidates,
Qdrant A2M counts, and latest nightly summary status. Do not copy DBs, reindex,
resync, rebuild projections, or repoint routes until a separate explicit
mutation task approves the intended canonical runtime source.

## Confirmed

- Canonical start path `/home/l4nd0/tenn` resolves to
  `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1`.
- Canonical branch at preflight was
  `migration/clean-runtime-baseline-reconstruct-v1` at
  `4b0fb54ecb54de50b1f29bbca044f118b9adf5c4`.
- Safe isolation was used because the canonical checkout had unrelated
  untracked task-card dirt:
  `docs/agent_tasks/worker_gpu_worker_provenance_env_parity_audit_v1_20260525.md`.
- Isolated worktree:
  `/home/l4nd0/tenn-a2m-news-projection-path-remediation-v1-20260525`.
- Isolated branch:
  `audit/a2m-news-projection-path-remediation-v1-20260525`.
- The task card validated and the shared registry had no active overlap before
  claim.
- Current Qdrant `news_chunks` is green with `22324` points, vector size `768`,
  and cosine distance.
- Current read-only Qdrant counts:
  `ticker=A2M` is `16`, `primary_ticker=A2M` is `16`,
  `tickers contains A2M` is `24`, and combined A2M is `24`.
- Qdrant A2M scroll was requested with `with_vector=false`.
- Current canonical NVMe paths checked:
  `reports/qual_context/news_articles.sqlite` absent;
  `reports/qual_context/news.sqlite` absent.
- Legacy `/mnt/sdb2/home/l4nd0/tenn/reports/qual_context/news_articles.sqlite`
  exists and has `2983` articles, `17459` entity links, `7237` article
  relevance rows, and `7` distinct A2M-linked articles.
- Legacy `/mnt/sdb2/home/l4nd0/tenn/reports/qual_context/news.sqlite` exists
  and has `24096` context chunks, `43` ticker-like A2M chunks, and `714`
  chunks where title/text contains A2M.
- Legacy SQLite contains A2M article `art_f249f18234a438ab0f84e6cb` with five
  context chunks, but current Qdrant has zero points for that article.
- Current Cockpit config declares `rag.news_context.db_path:
  reports/qual_context/news.sqlite`, but current Cockpit backend-api wiring
  builds a backend `QualContextReader` and does not pass `news_context_db_path`
  into `ToolRouter`.
- Current Cockpit/backend news context calls prefer backend `/rag/query`, which
  maps `source="news"` to Qdrant `query_news_chunks`.
- Current `ToolRouter.get_local_news_article()` still searches for
  `news_articles.sqlite` under the current repo root, repo parent, or
  `/workspace-reports`; none of those are the legacy `/mnt/sdb2` DB path.
- Current crontab is `0 2 * * * /home/l4nd0/tenn/financial-engine_v2/scripts/nightly_news.sh`.
- Current NVMe nightly log for May 25 exists, but no NVMe nightly summary JSON
  or canonical news SQLite files were found.
- Legacy `/mnt/sdb2` nightly summaries for May 22-24 exist. The May 24 summary
  reports Qdrant sync status `success` with `articles=0`, `chunks=0`,
  `upserted=0`, and SQLite fallback status `degraded` at the legacy DB path.

## Inferred

- Qdrant A2M evidence was populated from an earlier news article source
  consistent with the legacy `/mnt/sdb2` SQLite corpus, not from the current
  canonical NVMe SQLite paths.
- The current projection gap is not one problem. It is a combination of
  canonical path cutover, missing NVMe DB artifacts, and a current nightly
  runtime that did not materialize the NVMe fallback projection.
- The legacy `/mnt/sdb2` SQLite corpus is newer or broader than Qdrant for at
  least A2M article `art_f249f18234a438ab0f84e6cb`, so copying conclusions from
  either store to the other would be unsafe without an explicit parity task.
- The `rag.news_context.db_path` value is stale as an operational fallback in
  current backend-api mode unless a call path explicitly passes it to
  `ToolRouter.news_context_db_path`.

## Speculative

- The May 25 NVMe nightly run may have failed during fetch or early ingest, but
  the available log only proves it did not emit the expected summary/DB
  artifacts in the checked NVMe locations.
- There may be additional moved DB copies outside the checked canonical, NVMe,
  old HDD, and `/mnt/sdb2` paths. No broad full-home scan was used after the
  first broad find was stopped for scope control.

## DATA_MISSING

- Exact first date/time when the cron/news runtime switched from the legacy
  `/mnt/sdb2` working root to the NVMe `/home/l4nd0/tenn` root.
- Full May 25 nightly failure reason beyond the short NVMe log and missing
  summary artifact.
- A current sanctioned canonical source DB path for production use.
- Live chat synthesis proof, intentionally not invoked because it may write chat
  state or memory events.
- Full Qdrant-vs-SQLite parity diff, intentionally not run because the parent
  task forbids reindex/resync/load jobs and broad pipeline execution.

## Path And Config Mismatches

- Docs and defaults say canonical article DB:
  `reports/qual_context/news_articles.sqlite`.
  Current canonical NVMe file: absent.
  Legacy `/mnt/sdb2` file: present.
- Docs and defaults say canonical context DB:
  `reports/qual_context/news.sqlite`.
  Current canonical NVMe file: absent.
  Legacy `/mnt/sdb2` file: present but degraded/stale by its own May 24 summary.
- Current `/rag/query` news route does not read SQLite; it queries Qdrant
  `news_chunks`.
- Current Cockpit `news_context` config contains a SQLite `db_path`, but the
  normal backend-api reader ignores local embeddings and calls backend
  `/rag/query`.
- Current `get_local_news_article()` searches current repo-relative article DB
  candidates, not the legacy `/mnt/sdb2` path that actually has the DB.

## Root Cause Classification

- missing SQLite file: Confirmed for canonical NVMe paths.
- moved path: Confirmed. The files exist under legacy `/mnt/sdb2`, not under the
  current canonical NVMe runtime root.
- disabled projection: Inferred for current NVMe runtime. May 25 produced no
  summary/DB artifacts.
- stale config/docs: Confirmed. The config/docs name `news.sqlite`, but current
  primary news retrieval is Qdrant-backed and the configured SQLite path is not
  materialized in the canonical root.
- obsolete Qdrant source: Inferred. Qdrant contains older A2M evidence but is
  not in parity with the latest discovered legacy SQLite projection.
- loader drift: Confirmed at evidence level. Legacy SQLite has A2M article
  `art_f249f18234a438ab0f84e6cb`; Qdrant has zero points for it.
- Cockpit route mismatch: Confirmed for local article lookup and stale SQLite
  fallback expectations; not confirmed for backend `/rag/query`, which can reach
  Qdrant A2M.
- alias/entity-linking issue: Not supported by current evidence.

## Architecture Review

The proposed parent result is compliant with the system contract because it
does not change retrieval, embeddings, vector IDs, source labels, Cockpit route
semantics, or DB contents. The recommended child is read-only diagnostic
surface only. Any remediation that copies DB files, changes cron/runtime roots,
rebuilds `news.sqlite`, or repairs Qdrant parity is a separate mutation task and
must preserve backend retrieval authority, Qdrant cosine/768 invariants, and
fail-fast behavior.

## Safe Next Remediation

Recommended child task:
`a2m_news_projection_readonly_smoke_v1_20260525`.

Purpose: create a read-only smoke/report that checks canonical NVMe paths,
legacy candidates, Qdrant A2M counts, latest nightly status, and route
reachability classifications. It should not run ingestion, refresh, rebuild,
load, resync, alias canonicalization, or source-label changes.

Mutation remediation requiring explicit approval after the smoke:
repair the canonical news runtime materialization path and prove parity with a
bounded dry-read comparison before any rebuild or Qdrant write is approved.

## Validation Results

- Task-card syntax was verified from repo CLI help before use.
- Task card validation: passed.
- Registry list-active before claim: no active jobs.
- Registry check-overlap: passed.
- Registry claim: passed.
- JSON artifact validation: passed.
- `git diff --check`: passed.
- `agent_job_contract.py check-diff`: passed and wrote `diff-check.json`.
- Registry release: passed.
- Final registry list-active: this audit job is released; one unrelated active
  Query Orchestration job appeared after release
  (`strategy_lab_quantdinger_readonly_transport_progress_v1_20260525`).
- Final registry check-overlap rerun after that unrelated job appeared reports
  lane overlap. This is nonblocking for the completed audit because the A2M
  claim had already been released and the final worktree had no remaining
  changes.
- Final git status after audit commit: clean.

## Final Worktree Status

Closeout changed files are limited to the task card and report artifacts named
in `status.json` and `diff-check.json`. No code, DB, Qdrant, news-store,
service, env, cron, parser, extraction, scoring, source-label, or Cockpit
implementation file was changed.

Post-commit final worktree status: clean in the isolated audit worktree.

## Project Memory Save Recommendation

Save this result to Project Memory. The durable lesson is that after the NVMe
runtime cutover, A2M/news projection diagnostics must check both the current
canonical `/home/l4nd0/tenn` symlink target and the legacy `/mnt/sdb2` news DBs,
and must distinguish Qdrant reachability from SQLite projection materialization.
