# Preflight

## Session Declaration

Lane: Provenance
Branch: `preserve/dirty-work-20260430T065748Z`
Worktree: `/mnt/sdb2/home/l4nd0/tenn`
Execution mode: SAFE EXTENSION MODE
Intended files: allowed provenance/session/UI/test/report files only
Contested surfaces touched: `financial-engine_v2/backend/app/routes/cockpit_api.py`, `cockpit-ui/components/cockpit/chat/*`
Collision risk: MEDIUM
Decision: proceed

## Commands

- `pwd`: `/mnt/sdb2/home/l4nd0/tenn`
- `git branch --show-current`: `preserve/dirty-work-20260430T065748Z`
- `git rev-parse HEAD`: `ffffb2f2aeb8651c20216cfa4d98e204bd431d43`
- `git status --short`: only unrelated `?? tenn_prompt_contracts_response_guidelines.zip` before implementation
- `python scripts/agent_job_registry.py list-active`: `python` unavailable; rerun with `financial-engine_v2/.venv/bin/python`
- `financial-engine_v2/.venv/bin/python scripts/agent_job_registry.py list-active`: no active jobs; shared registry root `/mnt/sdb2/home/l4nd0/tenn/.git/tenn-agent-registry`

## Required Commits

- `3c147f74b1c6`: present (`source_label_semantics_present`)
- `b9ace36e5e02`: present (`a2m_ticker_news_selection_present`)
- `518c363dd446bf0025c728f68d9a3456e125668b`: present (`memory_backup_artifact_remediation_present`)

## Required Reports

- `reports/source_label_consistency_audit_20260506_150433/`: present
- `reports/source_label_semantics_20260506_144411/`: present
- A2M supporting reports: present

## Contract Boundary

Target layer: Analysis to Client presentation.

Relevant contract rules: backend is authority; Cockpit is client/orchestration only; retrieval remains backend-owned; no ingestion/extraction/vector/memory mutation; no silent source-backed claims without visible evidence.

What must not change: ingestion, extraction, retrieval ranking, Qdrant, `news.sqlite`, memory stores, financial truth semantics, and source-label taxonomy.

Why safe: the patch only preserves and renders existing evidence-role metadata, adds attached-source context as non-verifying API source metadata, and updates UI wording.
