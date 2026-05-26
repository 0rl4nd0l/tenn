# Memory Candidates

No memory writes were performed.

Candidate learnings for review:

- Nightly news root cause on 2026-05-26 was a missing canonical
  `financial-engine_v2/data/raw/asx_ticker_universe.txt`, not a cron-fire
  failure.
- `nightly_news.sh` should keep `NIGHTLY_NEWS_DRY_RUN=1` and
  `NIGHTLY_NEWS_LOG_DIR=...` available for no-mutation validation of scheduler
  observability.
- The first lock-up pass found 246 worktrees and 22 prunable entries; branch
  cleanup should remain a separate operator-approved repo-hygiene task.
- The current checkout had unrelated untracked task-card dirt:
  `docs/agent_tasks/github_outstanding_issue_creation_v1_20260526.md`.
