# Issue 242 Context Diagnostics Review Fixes

Status: `PR_OPENED`

Date: 2026-06-27T09:45:00+10:00

Branch: `safe/issue242-context-diagnostics-review-fixes-current-base-v1-20260627`

Base: `origin/migration/clean-runtime-baseline-reconstruct-v1@eb4a42910fd71077af4a389bd4a9f4400796921b`

PR: `https://github.com/0rl4nd0l/tenn/pull/448`

## Summary

This current-base replacement preserves the useful PR #438 route/UI changes for
issue #242 and fixes both P1 review blockers:

- Python `BackendApiClient` now sends `X-API-Key` on ticker context,
  verification context, and company dump reads when configured.
- `/api/context/company_dump` now passes the caller's `X-API-Key` through to
  ticker context assembly, so unauthenticated configured-key calls still redact
  diagnostics while authenticated calls keep source paths, extraction failures,
  and low-confidence rows.

The stale PR #438 worktree was not edited. Its implementation was ported onto a
fresh current-base worktree and tightened.

## Files Touched

- `docs/agent_tasks/issue242_context_diagnostics_review_fixes_current_base_v1_20260627.md`
- `financial-engine_v2/backend/app/api/context.py`
- `financial-engine_v2/backend/tests/test_context_diagnostics_route_auth.py`
- `financial-engine_v2/backend/tests/test_backend_api_client_context.py`
- `financial-engine_v2/cockpit/integrations/backend_api.py`
- `cockpit-ui/lib/api-client.ts`
- `cockpit-ui/lib/api-client.test.ts`
- `cockpit-ui/components/cockpit/verification/verification-screen.tsx`
- `docs/architecture/19_backend_api_surface.md`
- `reports/agent_jobs/issue242_context_diagnostics_review_fixes_current_base_v1_20260627/`

## Files Intentionally Not Touched

- Production DB, Qdrant, Redis, news stores, memory stores, source PDFs, gold
  labels, extraction prompts, parser routing, runtime services, and model/GPU
  config.
- Stale PR #438 worktrees and branches.
- GitHub labels, milestones, project fields, branch cleanup, and issue closeout.

## Validation Summary

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/issue242_context_diagnostics_review_fixes_current_base_v1_20260627.md` - PASS
- `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt pytest -q financial-engine_v2/backend/tests/test_context_diagnostics_route_auth.py financial-engine_v2/backend/tests/test_context_endpoints.py financial-engine_v2/backend/tests/test_backend_api_client_context.py` - PASS, 68 passed
- `PYTHONPATH=financial-engine_v2/backend uv run --with-requirements financial-engine_v2/backend/requirements.txt --with-requirements financial-engine_v2/backend/requirements-dev.txt ruff check financial-engine_v2/backend/app/api/context.py financial-engine_v2/cockpit/integrations/backend_api.py financial-engine_v2/backend/tests/test_context_diagnostics_route_auth.py financial-engine_v2/backend/tests/test_backend_api_client_context.py` - PASS
- `python3 -m py_compile financial-engine_v2/backend/app/api/context.py financial-engine_v2/cockpit/integrations/backend_api.py financial-engine_v2/backend/tests/test_context_diagnostics_route_auth.py financial-engine_v2/backend/tests/test_backend_api_client_context.py` - PASS
- `pnpm --dir cockpit-ui exec vitest run lib/api-client.test.ts` - BLOCKED, `Command "vitest" not found`
- First `git push -u origin safe/issue242-context-diagnostics-review-fixes-current-base-v1-20260627` - BLOCKED by missing repo-venv `ruff` and `pytest`
- `TENN_ALLOW_MISSING_HOOK_TOOLS=1 git push -u origin safe/issue242-context-diagnostics-review-fixes-current-base-v1-20260627` - PASS; hook ran markdown hygiene and pushed branch
- `gh pr create --repo 0rl4nd0l/tenn --base migration/clean-runtime-baseline-reconstruct-v1 --head safe/issue242-context-diagnostics-review-fixes-current-base-v1-20260627 ...` - PASS, opened PR #448

## DATA_MISSING

- Live backend/browser route proof was not run.
- Local frontend Vitest remains unavailable because `cockpit-ui` has no local
  `vitest` executable in this checkout.
- GitHub checks for PR #448 are pending or must be checked live before merge.

## Next Action

Monitor PR #448 checks and review. Close issue #242 only after PR merge
evidence, green GitHub checks, and canonical containment are verified.
