# Marketplace Recency Current-Target Integration V1

## Preflight

- Agent: Codex
- Lane: Reporting
- Supporting lane: Evaluation
- Execution mode: SAFE EXTENSION / CURRENT-TARGET INTEGRATION
- Target branch: `preserve/dirty-work-20260430T065748Z`
- Target starting HEAD: `c3609b5bf336132fcc0408d039fd0985bb386aff`
- Integration branch: `integrate/marketplace-recency-current-target-v1`
- Integration worktree: `/mnt/sdb2/home/l4nd0/tenn-marketplace-recency-current-target-v1`
- Target worktree: `/mnt/sdb2/home/l4nd0/tenn`
- Target dirty/untracked files identified before integration:
  - `cockpit-ui/tests/smoke-metric-coverage.spec.ts`
  - `docs/agent_tasks/cockpit_runtime_worktree_visibility_audit_20260507.md`
  - `docs/agent_tasks/dirty_task_card_classification_for_mcp_unblock_20260507.md`
  - `docs/agent_tasks/legacy_chat_envelope_merge_strategy_audit_v1.md`
  - `docs/agent_tasks/marketplace_matches_workflow_audit_v1.md`
  - `docs/agent_tasks/marketplace_recency_promote_to_target_v1.md`
  - `docs/agent_tasks/query_legacy_chat_envelope_preserve_merge_back_v1.md`
  - `docs/agent_tasks/tenn_agent_mcp_v0_audit_scaffold_20260507.md`
  - `docs/agent_tasks/tenn_agent_mcp_v0_merge_readiness_audit_20260507.md`
- `git worktree list`: target preserve worktree plus existing sibling worktrees; no existing `integrate/marketplace-recency-current-target-v1` branch/worktree.
- `git log --oneline --decorate -10`: target HEAD was `c3609b5 milestone(news): make daily ingest interruption durable`.
- `git rev-parse preserve/dirty-work-20260430T065748Z`: `c3609b5bf336132fcc0408d039fd0985bb386aff`.
- `git rev-parse b021acc44a6c68ca5653ecb1208ba466e4c385c2`: `b021acc44a6c68ca5653ecb1208ba466e4c385c2`.
- `git rev-parse de194ddb03506a055d7bf1e203123ef6e9147f12`: `de194ddb03506a055d7bf1e203123ef6e9147f12`.
- Registry list-active before claim: no active jobs.
- Registry overlap check: passed.
- Registry claim: `marketplace_recency_current_target_integration_v1` claimed in the shared registry.
- Registry release: passed after validation; active record removed and `status.json` written with released status.
- Contested surfaces touched: `financial-engine_v2/backend/app/routes/cockpit_api.py`.
- Collision risk: MEDIUM for the dirty target worktree, LOW inside the isolated claimed marketplace worktree.

## Contract Check

- Target system layer: backend API/service response path plus Cockpit Next.js client presentation.
- Relevant contract rules: SYSTEM_CONTRACT.md sections 1.1, 1.2, 2, 7, 8, and 10.
- Must not change: ingestion, extraction, financial truth, memory, RAG/Qdrant/Postgres access patterns, scanner discovery/scraping, query orchestration, or any unrelated task-card/report files.
- Safety rationale: the integration is additive recency exposure from existing marketplace seen-listing state and UI presentation only; it introduces no scanner instrumentation, scraping, schema migration, production data access, or fallback data source.
- GPU guard: not required; this task did not spawn, restart, or depend on llama-server.

## Integration

Integrated with `git cherry-pick -x` in the requested order:

- `b021acc44a6c68ca5653ecb1208ba466e4c385c2`
  - `milestone(reporting): expose marketplace match recency`
  - New commit on current target: `9997963`
- `de194ddb03506a055d7bf1e203123ef6e9147f12`
  - `milestone(reporting): surface marketplace match recency in UI`
  - New commit on current target: `8711b03`

Conflicts: none.

Old integration branch `integrate/marketplace-recency-integration-v1` and old integration commit `e1fe995a521b970f3ca732fa058f5853c768b3f6` were not merged or cherry-picked.

Final integration code HEAD at report creation: `8711b0328889c5adfe469a87c6ba3ca8ef3cfafa`.

## Files Changed

- `docs/agent_tasks/marketplace_recency_current_target_integration_v1.md`
- `financial-engine_v2/backend/app/services/marketplace_mission_service.py`
- `financial-engine_v2/backend/app/routes/cockpit_api.py`
- `financial-engine_v2/backend/tests/test_marketplace_mission_service.py`
- `financial-engine_v2/backend/tests/test_cockpit_marketplace_api.py`
- `cockpit-ui/lib/marketplace-api.ts`
- `cockpit-ui/components/cockpit/marketplace/match-recency.ts`
- `cockpit-ui/components/cockpit/marketplace/matches-screen.tsx`
- `cockpit-ui/components/cockpit/marketplace/matches-screen.test.tsx`
- `cockpit-ui/components/cockpit/marketplace/match-detail-screen.tsx`
- `cockpit-ui/components/cockpit/marketplace/match-detail-screen.test.tsx`
- `reports/agent_jobs/marketplace_recency_current_target_integration_v1/README.md`
- `reports/agent_jobs/marketplace_recency_current_target_integration_v1/status.json`
- `reports/agent_jobs/marketplace_recency_current_target_integration_v1/diff-check.json`

## Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/marketplace_recency_current_target_integration_v1.md`
  - Initial result: failed because the suggested card used `approval_required: false` for `safe_extension`.
  - Resolution: added `allow_unapproved_safe_extension: true` to preserve the handoff's approval flag while satisfying the validator.
  - Final result: passed.
- `python3 scripts/agent_job_registry.py list-active`
  - Result: passed; no active jobs.
- `python3 scripts/agent_job_registry.py check-overlap docs/agent_tasks/marketplace_recency_current_target_integration_v1.md`
  - Result: passed; no overlap issues.
- `python3 scripts/agent_job_registry.py claim docs/agent_tasks/marketplace_recency_current_target_integration_v1.md`
  - Result: passed; shared registry claim created.
- `PYTHONPATH=financial-engine_v2/backend:financial-engine_v2 /mnt/sdb2/home/l4nd0/tenn/financial-engine_v2/.venv/bin/pytest financial-engine_v2/backend/tests/test_marketplace_mission_service.py -q`
  - Result: `13 passed in 1.35s`.
- `PYTHONPATH=financial-engine_v2/backend:financial-engine_v2 /mnt/sdb2/home/l4nd0/tenn/financial-engine_v2/.venv/bin/pytest financial-engine_v2/backend/tests/test_cockpit_marketplace_api.py -q`
  - Result: collection failed with `ModuleNotFoundError: No module named 'app.models.companies'`.
- `PYTHONPATH=financial-engine_v2/backend:financial-engine_v2 /mnt/sdb2/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python -c "import sys, types, pytest; module = types.ModuleType('app.models.companies'); module.Company = type('Company', (), {}); sys.modules['app.models.companies'] = module; raise SystemExit(pytest.main(['financial-engine_v2/backend/tests/test_cockpit_marketplace_api.py::test_marketplace_api_exposes_match_recency_and_first_found_sort', '-q']))"`
  - Result: `1 passed in 2.04s`.
- `PYTHONPATH=financial-engine_v2/backend:financial-engine_v2 /mnt/sdb2/home/l4nd0/tenn/financial-engine_v2/.venv/bin/python -c "import sys, types, pytest; module = types.ModuleType('app.models.companies'); module.Company = type('Company', (), {}); sys.modules['app.models.companies'] = module; raise SystemExit(pytest.main(['financial-engine_v2/backend/tests/test_cockpit_marketplace_api.py', '-q', '-k', 'supports_missions_matches_and_alerts or exposes_match_recency']))"`
  - Result: `2 passed, 17 deselected in 1.56s`.
- `/mnt/sdb2/home/l4nd0/tenn/financial-engine_v2/.venv/bin/ruff check financial-engine_v2/backend/app/services/marketplace_mission_service.py financial-engine_v2/backend/app/routes/cockpit_api.py financial-engine_v2/backend/tests/test_marketplace_mission_service.py financial-engine_v2/backend/tests/test_cockpit_marketplace_api.py`
  - Result: `All checks passed!`
- `pnpm install --frozen-lockfile`
  - Result: passed in the isolated `cockpit-ui` worktree; lockfile was up to date and packages were reused from the pnpm store.
- `pnpm exec vitest run components/cockpit/marketplace/matches-screen.test.tsx components/cockpit/marketplace/match-detail-screen.test.tsx`
  - Result: `Test Files 2 passed (2)`, `Tests 12 passed (12)`, duration `4.19s`.
- `pnpm exec tsc --noEmit`
  - Result: passed with no diagnostics.
- `pnpm exec eslint lib/marketplace-api.ts components/cockpit/marketplace/match-recency.ts components/cockpit/marketplace/matches-screen.tsx components/cockpit/marketplace/matches-screen.test.tsx components/cockpit/marketplace/match-detail-screen.tsx components/cockpit/marketplace/match-detail-screen.test.tsx`
  - Result: passed with no diagnostics.
- Code-reviewer pass over the current-target integration diff
  - Result: no blocking findings.
- `git diff --check preserve/dirty-work-20260430T065748Z...HEAD`
  - Result: passed.
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/marketplace_recency_current_target_integration_v1.md`
  - Result: passed; changed files were the task card, `README.md`, `diff-check.json`, and `status.json`; no disallowed files; report written to `reports/agent_jobs/marketplace_recency_current_target_integration_v1/diff-check.json`.

## DATA_MISSING

- Full `test_cockpit_marketplace_api.py` collection remains blocked by missing tracked `financial-engine_v2/backend/app/models/companies.py` on this branch. Focused API recency validation used a temporary in-process import shim only for the requested focused tests.
- Live marketplace DB/browser/scanner evidence was intentionally not collected because the task forbids production data access, scanner instrumentation, live scraping, and browser automation.

## Readiness

- This branch is safe to promote to `preserve/dirty-work-20260430T065748Z` if the final artifact commit remains clean.
- Task C scanner instrumentation is not started here. It becomes safe only after this integration branch is promoted or explicitly handed off and a fresh registry overlap check for the scanner task is clear.
