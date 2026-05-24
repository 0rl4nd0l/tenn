# Cockpit Chat Visible Evidence Gap Labels

Job: `cockpit_chat_visible_evidence_gap_labels_v1_20260524`
Date: 2026-05-24
Status: implementation validated in isolated worktree

## Session Declaration

Lane: Query Orchestration
Branch: `safe/cockpit-chat-visible-evidence-gap-labels-v1-20260524`
Worktree: `/home/l4nd0/tenn-cockpit-chat-visible-evidence-gap-labels-v1-20260524`
Execution mode: SAFE EXTENSION
Intended files: task card, backend chat evidence guard, Cockpit chat route, focused backend tests, report artifacts
Contested surfaces touched: `financial-engine_v2/backend/app/routes/cockpit_api.py`
Collision risk: MEDIUM-HIGH, mitigated by isolated worktree, empty active registry, and exact file allowlist
Decision: proceeded after task-card validation, overlap check, and registry claim

## Confirmed Facts

- Canonical starting worktree was `/home/l4nd0/tenn-nvme-clean-baseline-reconstruct-v1` on `migration/clean-runtime-baseline-reconstruct-v1` at `8ec2e73108854e96a1c04c4c749ebe700cd4328c`.
- Shared-checkout `check-overlap` failed because unrelated untracked task cards were dirty outside this job's allowlist.
- A clean isolated worktree was created from the same HEAD.
- Shared registry had no active jobs before claim.
- Task-card validation passed in the isolated worktree.
- Registry `check-overlap` passed in the isolated worktree.
- Registry claim succeeded for this job.

## Contract Check

- Target layer: Analysis / Client presentation for the backend Cockpit chat response envelope.
- Relevant rules: backend remains authoritative; Cockpit must not perform retrieval; no fabrication; missing evidence must remain visible rather than being silently upgraded.
- Must not change: retrieval ranking, source selection, Qdrant, news stores, memory stores, extraction, parser routing, canonical financial truth, runtime topology, Docker, cron, systemd, model, or GPU configuration.
- Safety rationale: the patch runs after visible sources and metadata are already built. It labels and qualifies the returned answer text; it does not retrieve, rank, mutate data stores, or rewrite canonical facts.

## Implementation

- Added `apply_visible_evidence_gap_labels()` in `chat_evidence_guard.py`.
- The presentation guard detects `market_data_missing`, `unsupported_or_not_verified`, `metric_extraction_missing`, and `missing_required_evidence` from response metadata and missing-evidence categories.
- When those labels are present, the returned answer text now begins with a `DATA_MISSING / evidence gaps` block naming the exact gap labels.
- Company-memory and market-memory sections are relabeled as context-only when market/technical evidence is missing.
- Company-memory bullets under a market-data gap are prefixed as context-only memory notes, so price movement lines are not displayed as verified market conclusions.
- The evidence guard now treats explicit text such as `no canonical financial rows were returned` as `metric_extraction_missing`.
- Operational YouTube recent-video listing output is excluded from claim-family detection to avoid showing a false evidence-gap banner for video titles.
- `_build_chat_ui_metadata()` remains the metadata owner; `cockpit_api.py` applies the presentation guard after metadata enrichment for both streaming and non-streaming `/api/cockpit/chat` paths.

## Tests Added Or Updated

- `test_missing_canonical_financial_rows_marks_metric_extraction_missing`
- `test_visible_gap_labels_qualify_company_memory_price_context`
- Existing price-trend and metric route tests now assert the visible answer text includes the gap block.
- Stateless smoke route test now covers CSL-style hidden gaps, company-memory price lines, and metric extraction gaps.
- Existing missing-financial-rows stream test now asserts `metric_extraction_missing` appears visibly.
- Existing YouTube recent-video stream test remains unchanged and verifies operational list output is not prefixed with a gap banner.

## Code Review

Code-reviewer pass result: no critical findings, no warnings, no suggestions.

Review inputs:
- `git diff` for `chat_evidence_guard.py`, `cockpit_api.py`, and focused backend tests.
- Focused compile, pytest, ruff, and diff checks listed below.

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_chat_visible_evidence_gap_labels_v1_20260524.md`: PASS.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/cockpit_chat_visible_evidence_gap_labels_v1_20260524.md`: PASS in isolated worktree.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/cockpit_chat_visible_evidence_gap_labels_v1_20260524.md`: PASS.
- `PYTHONPYCACHEPREFIX=/tmp/tenn_visible_gap_labels_pycache python3 -m compileall -q financial-engine_v2/backend/app/services/chat_evidence_guard.py financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_chat_evidence_guard.py financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py`: PASS.
- `/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python -m pytest -q financial-engine_v2/backend/tests/test_chat_evidence_guard.py financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py`: PASS, `69 passed`.
- `/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python -m ruff check financial-engine_v2/backend/app/services/chat_evidence_guard.py financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_chat_evidence_guard.py financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py`: PASS.
- `git diff --check`: PASS.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_chat_visible_evidence_gap_labels_v1_20260524.md`: PASS.
- `python3 scripts/agent_job_registry.py release cockpit_chat_visible_evidence_gap_labels_v1_20260524`: PASS.
- `python3 scripts/agent_job_registry.py list-active`: PASS, empty `active_jobs`.

## DATA_MISSING

- `graphify-out/GRAPH_REPORT.md` is absent in both the shared and isolated worktrees.
- This task used focused offline route tests; it did not restart the backend or run a live CSL prompt against the currently served container.

## Files Changed

- `docs/agent_tasks/cockpit_chat_visible_evidence_gap_labels_v1_20260524.md`
- `financial-engine_v2/backend/app/services/chat_evidence_guard.py`
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/backend/tests/test_chat_evidence_guard.py`
- `financial-engine_v2/backend/tests/test_cockpit_api_chat_stream.py`
- `reports/agent_jobs/cockpit_chat_visible_evidence_gap_labels_v1_20260524/README.md`
- `reports/agent_jobs/cockpit_chat_visible_evidence_gap_labels_v1_20260524/status.json`
- `reports/agent_jobs/cockpit_chat_visible_evidence_gap_labels_v1_20260524/validation.json`
- `reports/agent_jobs/cockpit_chat_visible_evidence_gap_labels_v1_20260524/diff-check.json`

## Files Intentionally Not Touched

- Qdrant, news stores, memory stores, extraction, parser routing, canonical financial truth, retrieval ranking, source selection, runtime topology, Docker, cron, systemd, model/GPU configuration, frontend UI, and old worktrees.

## Required Final Report Template

Files changed:
- See "Files Changed".

Files inspected:
- `CLAUDE.md`
- `docs/architecture/SYSTEM_CONTRACT.md`
- `docs/entrypoints.md`
- `docs/architecture/13_security_and_secrets.md`
- `/home/l4nd0/.claude/projects/-mnt-sdb2-home-l4nd0-tenn/memory/MEMORY.md`
- `/home/l4nd0/.codex/memories/MEMORY.md`
- prior guard/stateless smoke reports
- backend guard, route, service, and test files listed above

Lane:
- Query Orchestration

Execution mode:
- SAFE EXTENSION

Collision risk:
- MEDIUM-HIGH, mitigated by isolated worktree and exact allowlist.

Validation run:
- See "Validation".

Validation result:
- Focused compile, pytest, ruff, diff checks, task-card `check-diff`, and registry release passed.

Files intentionally not touched:
- See "Files Intentionally Not Touched".

Remaining blockers:
- Live backend must serve this commit before a new stateless CSL live smoke can prove runtime behavior.

Next safe step:
- After integration/reload, rerun the stateless CSL smoke and verify response text begins with the evidence-gap block.
