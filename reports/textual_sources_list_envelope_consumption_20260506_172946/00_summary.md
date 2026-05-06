# Summary

G003 is implemented for the local Textual `/sources list` and `/sources show <n>` command path.

The Textual source display now consumes `QueryOrchestrator.evidence_envelope` when present, preserves envelope role labels and source status, and renders explicit fields such as `claim_verified`, `no_hit`, `degraded`, `missing_required_evidence`, `item_count`, and `error`. Legacy source payloads without an envelope now render with an explicit fallback warning that the listed sources are inspection-only and not verification labels.

No ingestion, Qdrant, `news.sqlite`, memory stores, retrieval ranking, financial truth extraction, source drawer UI, or legacy `/api/chat` code was touched.

Implementation files changed:

- `financial-engine_v2/cockpit/core/chat.py`
- `financial-engine_v2/cockpit/tests/test_slash_commands.py`
- `financial-engine_v2/cockpit/tests/test_chat_orchestrator_integration.py`

Coordination notes:

- Task card created and validated: `docs/agent_tasks/reporting_textual_sources_list_v1.md`
- Shared registry had no active jobs.
- Registry claim failed because the worktree already contained unrelated dirty Cockpit web/home/design files outside this task card.
- Dirty files did not overlap the Python/Textual source-display files changed here.

Commit status: not committed because unrelated dirty work remains in the shared worktree and task-card claim/check-diff could not pass with those unrelated files present.
