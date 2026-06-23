---
job_id: cockpit_bff_proxy_module_deepening_v1_20260623
title: Cockpit BFF proxy module deepening
lane: Evaluation
supporting_lanes:
  - Evaluation
  - Repo Hygiene
owner: Codex
approval_required: false
allow_unapproved_safe_extension: true
timeout_seconds: 7200
output_dir: reports/agent_jobs/cockpit_bff_proxy_module_deepening_v1_20260623
mutation_mode: safe_extension
production_data_access: false
github_mutation_allowed: true
allowed_files:
  - docs/agent_tasks/cockpit_bff_proxy_module_deepening_v1_20260623.md
  - reports/agent_jobs/cockpit_bff_proxy_module_deepening_v1_20260623/**
  - reports/agent_jobs/cockpit_bff_proxy_module_deepening_v1_20260623/STATE.md
  - reports/agent_jobs/cockpit_bff_proxy_module_deepening_v1_20260623/DECISIONS.md
  - reports/agent_jobs/cockpit_bff_proxy_module_deepening_v1_20260623/validation.json
  - reports/agent_jobs/cockpit_bff_proxy_module_deepening_v1_20260623/CODE_REVIEW.json
  - reports/agent_jobs/cockpit_bff_proxy_module_deepening_v1_20260623/NEXT_GOAL.md
  - reports/agent_jobs/cockpit_bff_proxy_module_deepening_v1_20260623/status.json
  - cockpit-ui/lib/proxy.ts
  - cockpit-ui/lib/proxy.test.ts
  - cockpit-ui/lib/watchlist-routes.test.ts
  - cockpit-ui/app/api/cockpit/watchlist/route.ts
  - cockpit-ui/app/api/cockpit/watchlist/[ticker]/route.ts
docs_impact: DOCS_NOT_REQUIRED
docs_checked:
  - reports/agent_jobs/repo_architecture_development_board_v1_20260623/BOARD.md
  - reports/agent_jobs/repo_dev_import_runtime_entrypoint_remediation_v1_20260623/NEXT_GOAL.md
  - cockpit-ui/lib/proxy.ts
docs_changed:
  - NONE
docs_followup: NONE
reason: "Internal Cockpit BFF helper refactor with no API, operator workflow, runtime, or data contract change."
task_tier: medium
recommended_model: "standard coding model"
actual_model: "Codex GPT-5"
why_this_model: "The change is a focused TypeScript route-helper refactor with existing route tests."
worker_model_allowed: false
worker_decision_limit: "main orchestrator only; no subagent needed for this narrow slice."
escalation_needed: false
---

# Cockpit BFF Proxy Module Deepening

## Objective

Implement board recommendation 3 in one narrow slice by deepening the Cockpit
BFF proxy helper and migrating the watchlist route cluster away from repeated
manual backend forwarding code.

## Scope

Allowed:

- Add a tested helper in `cockpit-ui/lib/proxy.ts` for common backend request
  forwarding and upstream response construction.
- Add focused proxy helper tests.
- Migrate only the watchlist route cluster:
  - `cockpit-ui/app/api/cockpit/watchlist/route.ts`
  - `cockpit-ui/app/api/cockpit/watchlist/[ticker]/route.ts`
- Keep request headers, request bodies, no-store cache behavior, backend URL
  resolution, status propagation, content-type propagation, and error payloads
  behaviorally compatible.
- Write validation and closeout artifacts under the report directory.

Forbidden:

- No backend, runtime, Docker, service, DB, Qdrant, Redis, news, memory-store,
  extraction, source-document, model, GPU, `.env`, lockfile, package manifest,
  CI, host-global, or production data mutation.
- No broad Cockpit UI redesign, frontend component changes, route-wide
  mechanical migration, or API contract change.
- No unrelated cleanup, branch deletion, force-push, reset, stash, clean,
  rebase, or worktree deletion.

## Required Preflight

1. Run `tenn-git-guard` preflight.
2. Validate this task card.
3. Run registry `list-active --read-only`.
4. Run task ledger validation.
5. Confirm no active overlapping PR for Cockpit proxy work.

## Required Validation

- `python3 scripts/agent_job_contract.py validate docs/agent_tasks/cockpit_bff_proxy_module_deepening_v1_20260623.md`
- `pnpm --dir cockpit-ui exec vitest run lib/proxy.test.ts lib/watchlist-routes.test.ts`
- `pnpm --dir cockpit-ui exec tsc --noEmit`
- `pnpm --dir cockpit-ui exec eslint lib/proxy.ts lib/proxy.test.ts lib/watchlist-routes.test.ts app/api/cockpit/watchlist/route.ts app/api/cockpit/watchlist/[ticker]/route.ts`
- `git diff --check`
- `python3 scripts/agent_job_contract.py check-diff docs/agent_tasks/cockpit_bff_proxy_module_deepening_v1_20260623.md --no-write-report`

## Done Criteria

- The watchlist BFF route cluster uses the shared proxy helper.
- Tests prove URL construction, header/body forwarding, response propagation,
  and existing watchlist behavior.
- Diff remains inside allowed files.
- Closeout records validation, docs impact, and remaining risks.
