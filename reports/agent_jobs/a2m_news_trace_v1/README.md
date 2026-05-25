# A2M News Trace v1

Generated: 2026-05-25T15:18:15+10:00

## Scope

- GitHub issue: #38.
- Lane: Query Orchestration.
- Supporting lanes: Provenance, Reporting, Memory.
- Execution mode: AUDIT ONLY.
- Target system layer: retrieval/provenance evidence reporting only.
- Contract boundary: no ingestion, news backfill, SQLite writes, Qdrant writes, retrieval code edits, ranking edits, synthesis edits, source-label edits, runtime changes, service starts, chat calls, memory writes, or production data mutation.

## Preflight Declaration

- Agent: Codex.
- Branch: `audit/repo-hygiene-safe-audits-v1-20260525`.
- Worktree: `/home/l4nd0/tenn-repo-hygiene-audits-v1-20260525`.
- Pre-closeout HEAD: `de5545ff4579`.
- Pre-closeout git status: clean against origin before this task card/report was added.
- Registry before claim: `active_jobs: []`.
- Intended files: `docs/agent_tasks/a2m_news_trace_v1.md` and this issue-exact report directory only.
- Contested surfaces touched: none.
- Collision risk: LOW.
- Decision: proceed report-only.

## Executive Result

Issue #38 is safe to close as audit acceptance met. This closeout does not claim that every news/runtime hardening concern is solved.

The audit acceptance criteria are met by the existing A2M artifact family:

- Root cause was narrowed from a simple alias/ingestion absence to a retrieval/projection/path-parity failure class.
- Live read-only evidence later confirmed Qdrant `news_chunks` contains A2M evidence: 24 A2M-matching chunks across 4 unique articles, with collection point count unchanged before and after the trace.
- SQLite source/projection parity remains `DATA_MISSING` because checked canonical/local `news.sqlite` and `news_articles.sqlite` paths were absent.
- Retrieval parity remediation already exists in current branch history at `fa776ce9`, changing backend news ticker matching across `ticker`, `primary_ticker`, and `tickers`, with focused and broad news/source-label tests reported as passing in its integration report.

This issue is therefore closed as an audit/report closeout. Remaining SQLite/projection health and live synthesis visibility are backlog items, not silently fixed by this closeout.

## Evidence References

- Static/blast-radius audit: `reports/agent_jobs/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519/README.md`.
- Static trace map: `reports/agent_jobs/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519/a2m_trace_map.json`.
- Blast-radius candidates: `reports/agent_jobs/a2m_news_trace_entity_linking_blast_radius_audit_v1_20260519/blast_radius_candidates.json`.
- Projection path discovery: `reports/agent_jobs/a2m_news_projection_path_discovery_v1_20260524/README.md`.
- Projection parity matrix: `reports/agent_jobs/a2m_news_projection_path_discovery_v1_20260524/path_parity_matrix.json`.
- Live read-only trace: `reports/agent_jobs/a2m_news_live_trace_readonly_v1_20260524/README.md`.
- Qdrant probe: `reports/agent_jobs/a2m_news_live_trace_readonly_v1_20260524/qdrant_probe.json`.
- SQLite inventory: `reports/agent_jobs/a2m_news_live_trace_readonly_v1_20260524/sqlite_inventory.json`.
- Retrieval parity integration: `reports/agent_jobs/news_retrieval_parity_a2m_integration_v1_20260520/README.md`.

## Issue Acceptance Matrix

Confirmed storage state: Qdrant `news_chunks` is reachable in the live read-only trace and contains A2M evidence. SQLite source/projection files were absent at checked paths, so SQLite parity remains `DATA_MISSING`.

Entity-linking path analysis: the static audit confirms A2M aliases and symbol forms are configured and tested; live source SQLite/entity-link row parity remains unavailable because source SQLite files were absent.

Retrieval/ranking trace: static and live traces separate `/rag/query`, backend chat HybridRetriever, and source-label behavior. The current branch contains the retrieval parity integration commit `fa776ce9`.

Synthesis/runtime observations: live chat synthesis was intentionally not invoked because it can write chat/report/memory artifacts.

Source-label observations: existing integration evidence reports preservation of `local_news_context` / `context_only` behavior and no promotion to `claim_verified` without direct support.

Isolated or systemic: blast radius is classified as medium/systemic for linked-ticker and route-parity behavior, not isolated to one A2M alias.

Other affected tickers/entities: the static audit names multi-ticker articles, brand/company aliases, noisy/generic aliases, and stopword-like tickers as the affected classes.

Proposed root-cause fix surface: backend news retrieval/filtering path parity. That remediation exists in current branch history at `fa776ce9`.

Regression fixture recommendations: linked-ticker payloads, ticker-list-only payloads, route parity, ranking retention, source-label/no-hit, freshness, and negative alias fixtures are documented in the static audit.

## DATA_MISSING

- Direct parity from source news SQLite rows to Qdrant payloads.
- Whether canonical `news.sqlite` / `news_articles.sqlite` moved to an unchecked path, or whether fallback refresh is skipped/writing elsewhere.
- Live chat synthesis visibility for A2M, intentionally not invoked during audit closeout.
- Current nightly/fallback-refresh success evidence.
- Full route parity across every live user-facing news surface after integration.

## Boundary Statement

This closeout did not reindex, resync, backfill, ingest, write SQLite, write Qdrant, call live chat synthesis, change source-label taxonomy, edit retrieval/ranking/synthesis code, mutate memory, mutate financial truth, start or restart services, or change model/runtime config.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/a2m_news_trace_v1.md`: passed.
- `python3 scripts/agent_job_registry.py list-active`: passed; no active jobs.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/a2m_news_trace_v1.md`: passed.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/a2m_news_trace_v1.md`: passed.
- `python3 -m json.tool` on A2M trace map, blast-radius candidates, live retrieval trace, live Qdrant probe, and projection parity matrix: passed.
- `git merge-base --is-ancestor fa776ce9 HEAD`: passed, confirming the parity integration commit is in current branch history.
- `git diff --check`: passed.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/a2m_news_trace_v1.md`: passed.
- `python3 scripts/agent_job_registry.py release a2m_news_trace_v1`: passed.
- `python3 scripts/agent_job_registry.py list-active` after release: passed; no active jobs reported.
