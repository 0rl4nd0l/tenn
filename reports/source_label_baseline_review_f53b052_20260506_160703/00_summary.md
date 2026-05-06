# Summary

Lane: Provenance
Secondary lane: Reporting
Agent: Codex
Branch: `preserve/dirty-work-20260430T065748Z`
Worktree: `/home/l4nd0/tenn` via `/mnt/sdb2/home/l4nd0/tenn`
Execution mode: AUDIT MODE, then SAFE EXTENSION MODE for report artifacts only
Collision risk: LOW for this audit/report write; reviewed commit touches MEDIUM provenance/reporting surfaces

## Contract Check

Target system layer: CLIENT, with backend API serialization at the analysis/client boundary.

Relevant contract rules: backend remains source of truth; Cockpit remains client/orchestration only; no ingestion, extraction, storage truth, vector, memory, or retrieval-ranking change is allowed.

Must not change: canonical financial facts, source/evidence truth, Qdrant/news runtime state, memory stores, Holdings/Marketplace routing, extraction/parser logic, or chat synthesis behavior.

Safety: the audit did not mutate databases, restart services, run ingestion, run backfills, or touch the untracked zip.

## Verdict

`f53b052` is accepted as a baseline because focused checks show labels are persisted for delivered assistant turns, returned on chat-session reload, hydrated into frontend chat messages, and rendered with role-specific wording instead of generic source-backed wording.

The commit does not create the full future taxonomy. The taxonomy definitions already existed in the parent commit; this change mainly propagates and preserves them, plus classifies attached-source context as `context_only`.
