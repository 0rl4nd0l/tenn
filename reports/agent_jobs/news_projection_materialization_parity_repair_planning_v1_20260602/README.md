# News Projection Materialization Parity Repair Planning

Generated: 2026-06-02T01:56:44+10:00

## Executive Result

Issue #83 is resolved as an audit/planning deliverable, not as a data repair.
Current read-only evidence shows the live news artifact root has advanced from
the older "both projection files absent" state to a partial state:
`news_articles.sqlite` exists under the live NVMe artifact root, but the
canonical RAG projection `news.sqlite` is still absent.

That means A2M/news projection is not fixed. The next safe step is a separate,
approval-gated projection materialization task that builds or refreshes
`news.sqlite` from the approved current article source and then runs parity and
status-route validation. This audit did not run ingestion, rebuilds, Qdrant
mutation, SQLite writes, service restarts, or chat/session requests.

## Confirmed

- Canonical news architecture still requires one production RAG DB at
  `reports/qual_context/news.sqlite` per `docs/architecture/15_news_substrate.md`.
- Cockpit config still points `rag.news_context.db_path` at
  `reports/qual_context/news.sqlite`.
- The read-only status builder reports `canonical_sqlite_projection=partial`
  when it resolves the current live artifact root at
  `/mnt/tenn-nvme2/tenn/financial-engine_v2/reports/qual_context`.
- At that live artifact root, `news_articles.sqlite` exists and has 225 article
  rows, 13 A2M-like title/body matches, and latest article timestamp
  `2026-05-27T07:02:01Z`.
- At that same live artifact root, `news.sqlite` is absent.
- Legacy `/mnt/sdb2/home/l4nd0/tenn/reports/qual_context` still has both
  SQLite files and A2M-like evidence, but it is not the current consumer.
- Already-running backend, Next, and Qdrant services were not available on
  localhost during this audit; no services were started.

## DATA_MISSING

- Live Qdrant `news_chunks` count and A2M parity for the current moment:
  `127.0.0.1:6333` refused connection.
- Live backend `/api/cockpit/news/status` payload:
  `127.0.0.1:8000` refused connection.
- Live Next `/api/cockpit/news/status` payload:
  `127.0.0.1:3000` refused connection.
- A safe current chat synthesis proof: not attempted because chat/session routes
  can write state and #83 does not approve that mutation surface.
- A current nightly status artifact in this isolated branch:
  `reports/ops_checks/nightly/nightly_news_2026-06-01_020001.status.json` is
  not present on this branch.

## Decision

Selected next step: **projection materialization in a separate approved task**.

Reason:
- The current blocker is not that `news_articles.sqlite` is absent; it is that
  the canonical RAG projection `news.sqlite` is absent at the live artifact
  root.
- Qdrant repair is not justified from current-turn evidence because Qdrant was
  not reachable for live read-only inspection.
- Status-only work is already present in code and tests; it preserves split
  truth but cannot make article-detail fallback or SQLite projection parity
  true.
- Scheduler repair may still be needed after projection materialization, but
  this audit lacks a current nightly run artifact proving scheduler root cause.

## No Mutation Attestation

- No ingestion, backfill, reindex, resync, projection rebuild, DB copy, symlink,
  or data repair was run.
- No Qdrant, SQLite, Postgres, news store, memory, company memory, market
  memory, thesis memory, canonical financial truth, runtime config, service
  config, Docker, systemd, cron, or GPU/model state was mutated.
- Only this task card and report bundle were changed.

## Suggested Follow-Up Task

Create a separate safe-extension task card for:

- validating `/mnt/tenn-nvme2/tenn/financial-engine_v2/reports/qual_context/news_articles.sqlite`
  as the approved source;
- building or refreshing only
  `/mnt/tenn-nvme2/tenn/financial-engine_v2/reports/qual_context/news.sqlite`
  through the canonical pipeline;
- running `scripts/verify_news_context_db.py`;
- verifying `/api/cockpit/news/status` reports `canonical_sqlite_projection=present`;
- probing Qdrant read-only after services are available;
- keeping chat synthesis as `DATA_MISSING` unless a separate safe chat-smoke
  task explicitly owns it.
