# Next Repair Decision

Decision: projection materialization in a separate approved task.

Do not run the repair from this audit. The currently resolved live artifact root
is partial: `news_articles.sqlite` exists, but canonical `news.sqlite` is
absent. The repair should therefore materialize or refresh the canonical SQLite
RAG projection from the approved article source, then verify the projection and
status route.

Rejected alternatives:

- No-op: rejected because canonical `news.sqlite` is absent.
- Docs/status only: rejected because status reporting already preserves the
  split truth and cannot create the missing projection.
- Qdrant repair: not selected because live Qdrant was unavailable for current
  read-only proof.
- Scheduler repair: deferred until after materialization, because current-turn
  evidence did not include a fresh nightly status artifact proving scheduler
  root cause.

Required constraints for the follow-up:

- Separate task card and registry claim.
- Explicit approval for `safe_extension`.
- Exact allowed output path for `news.sqlite`.
- No DB copies or symlink shortcuts.
- No Qdrant writes unless separately approved and proven necessary.
- No chat/session smoke unless a separate task owns that write risk.
