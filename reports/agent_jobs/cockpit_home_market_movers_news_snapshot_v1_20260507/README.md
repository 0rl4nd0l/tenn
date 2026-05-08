# Cockpit Home Market Movers / News Snapshot v1

Status: audit-only, implementation blocked.

The task card validated, but the agent registry refused the job claim because an unrelated untracked file already exists outside this task card:

- `docs/agent_tasks/news_pipeline_dirty_file_classification_v1_20260507.md`

No backend or frontend product files were changed.

Key result:

- Market movers remain `NO_MARKET_MOVERS_ENDPOINT` / `DATA_MISSING`.
- A deterministic local news snapshot source exists in `reports/qual_context/news_articles.sqlite` and `reports/qual_context/news.sqlite`, but wiring was deferred until the job can be claimed safely.

See `INVESTIGATION.md` for evidence and next steps.
